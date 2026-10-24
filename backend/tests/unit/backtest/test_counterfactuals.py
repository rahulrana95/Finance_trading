"""Every candidate simulated alone until its exit; labels readable only once closed."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

from fintrade.backtest.candidates import CandidateConfig
from fintrade.backtest.counterfactuals import Simulation, SkippedDay, counterfactuals
from fintrade.backtest.data import InMemoryMarketData
from fintrade.backtest.exits import RuleExitPolicy
from fintrade.core.instruments import Structure
from fintrade.core.rules.strategy_config import ExitConfig
from tests.support.backtest import SettleFill
from tests.support.calendar import expiry_calendar
from tests.support.chain import FORWARD, chain_history
from tests.support.instruments import EXPIRY

MON, TUE, WED = date(2026, 10, 26), date(2026, 10, 27), date(2026, 10, 28)
WEEK = [MON, TUE, WED, date(2026, 10, 29), date(2026, 10, 30), date(2026, 11, 2)]
STRIKES = range(22000, 28550, 50)
NEVER = ExitConfig(profit_target_pct_of_max=Decimal(100), stop_loss_multiple_of_credit=Decimal(50))
GRID = CandidateConfig(widths=(Decimal(200),))


def _sim(forwards: dict[date, float], exit_config: ExitConfig = NEVER, **kw: object) -> Simulation:
    data = InMemoryMarketData(chain_history(forwards, EXPIRY, STRIKES))
    sim = Simulation(
        data=data,
        calendar=expiry_calendar(),
        lot_sizes={EXPIRY: 65},
        fills=SettleFill(),
        exit=RuleExitPolicy(expiry_calendar(), exit_config),
        candidates=GRID,
    )
    return replace(sim, **kw)  # type: ignore[arg-type]


def test_quiet_week_every_candidate_held_to_the_time_exit_and_profits() -> None:
    run = counterfactuals(_sim(dict.fromkeys(WEEK, FORWARD)), [MON])
    assert len(run.outcomes) == 9
    assert run.unfinished == []
    for outcome in run.outcomes:
        assert outcome.decision_day == MON
        assert outcome.result.exit_day == WEEK[-1]
        assert outcome.result.reasons == ("time_exit",)
        assert outcome.result.gross_pnl > 0


def test_crash_puts_lose_calls_win() -> None:
    forwards = {MON: FORWARD, TUE: FORWARD * 0.96}
    run = counterfactuals(_sim(forwards, ExitConfig()), [MON])
    by_structure = {
        (o.candidate.structure, o.candidate.target_delta): o.result for o in run.outcomes
    }
    assert len(by_structure) == 9
    put = by_structure[(Structure.BULL_PUT, Decimal("0.12"))]
    assert put.exit_day == TUE
    assert "stop_loss" in put.reasons
    assert put.net_pnl < 0
    assert all(r.net_pnl < 0 for (s, _), r in by_structure.items() if s is Structure.IRON_CONDOR)


def test_same_position_simulated_once() -> None:
    grid = replace(GRID, target_deltas=(Decimal("0.10"), Decimal("0.1000001")))
    run = counterfactuals(_sim(dict.fromkeys(WEEK, FORWARD), candidates=grid), [MON])
    first, second = run.outcomes[0], run.outcomes[1]
    assert first.candidate.position == second.candidate.position
    assert first.result is second.result


def test_data_running_out_leaves_candidates_unfinished() -> None:
    run = counterfactuals(_sim({MON: FORWARD, TUE: FORWARD}))
    assert run.outcomes == []
    assert {day for day, _ in run.unfinished} == {MON, TUE}
    assert len(run.unfinished) == 18


def test_days_without_expiry_or_lot_size_are_skipped_with_reason() -> None:
    late = date(2026, 11, 20)  # no expiry 6-13 days ahead in the test calendar
    sim = _sim({MON: FORWARD, late: FORWARD}, lot_sizes={EXPIRY: None})
    run = counterfactuals(sim)
    assert run.skipped == [
        SkippedDay(MON, f"lot size unknown for {EXPIRY}"),
        SkippedDay(late, "no entry expiry"),
    ]


def test_labels_readable_only_after_the_trade_closed() -> None:
    run = counterfactuals(_sim(dict.fromkeys(WEEK, FORWARD)), [MON])
    assert run.known_before(WEEK[-1]) == []
    assert run.known_before(EXPIRY) == run.outcomes

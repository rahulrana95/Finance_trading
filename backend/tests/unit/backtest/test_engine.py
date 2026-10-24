from datetime import date
from decimal import Decimal

import pytest

from fintrade.backtest.engine import BacktestConfig, DecisionKind, ReplayEngine, Strategy
from fintrade.core.charges import order_charges
from fintrade.core.errors import DataError
from fintrade.core.instruments import Side
from tests.support.backtest import ExitOnDays, ScriptedEntry, SettleFill, market, spread_bars
from tests.support.calendar import expiry_calendar
from tests.support.instruments import EXPIRY, bull_put

MON, TUE, WED, THU = (date(2026, 10, d) for d in (26, 27, 28, 29))
CONFIG = BacktestConfig(capital=Decimal(5_000_000), margin_available=Decimal(5_000_000))
LOTS: dict[date, int | None] = {EXPIRY: 65}


def _engine(
    entry: ScriptedEntry,
    exit_: ExitOnDays,
    prices: dict[date, tuple[str, str]],
    lots: dict[date, int | None] | None = None,
) -> ReplayEngine:
    data = market(spread_bars(bull_put(), prices))
    strategy = Strategy(entry=entry, exit=exit_, fills=SettleFill())
    return ReplayEngine(data, strategy, expiry_calendar(), LOTS if lots is None else lots, CONFIG)


PRICES = {MON: ("42.50", "12.00"), TUE: ("30.00", "8.00"), WED: ("20.00", "5.00")}


def test_trade_opened_marked_and_closed_with_costs() -> None:
    result = _engine(ScriptedEntry({MON}), ExitOnDays({WED}), PRICES).run()
    (closed,) = result.closed
    assert (closed.trade.entry_day, closed.exit_day, closed.reasons) == (MON, WED, ("scripted",))
    assert closed.gross_pnl == Decimal("2015.00")  # ((42.50 - 20) - (12 - 5)) x 130
    entry_costs = (
        order_charges(Side.SELL, Decimal("42.50"), 130, MON).total
        + order_charges(Side.BUY, Decimal(12), 130, MON).total
    )
    exit_costs = (
        order_charges(Side.BUY, Decimal(20), 130, WED).total
        + order_charges(Side.SELL, Decimal(5), 130, WED).total
    )
    assert closed.trade.entry_costs == entry_costs == Decimal("58.52")
    assert closed.net_pnl == Decimal("2015.00") - entry_costs - exit_costs
    assert (closed.trade.max_profit, closed.trade.max_loss) == (
        Decimal("3965.00"),
        Decimal("22035.00"),
    )
    assert result.still_open == []


def test_daily_equity_counts_open_value_and_charges() -> None:
    result = _engine(ScriptedEntry({MON}), ExitOnDays({WED}), PRICES).run()
    mon, tue, wed = result.daily
    assert mon.realized_total == 0
    assert mon.open_mtm == Decimal("-58.52")  # entry charges only
    assert tue.open_mtm == Decimal("1105.00") - Decimal("58.52")  # (12.50 - 4) x 130 - charges
    assert wed.open_mtm == 0
    assert wed.realized_total == result.closed[0].net_pnl


def test_decisions_logged_every_day() -> None:
    entry = ScriptedEntry({MON})
    result = _engine(entry, ExitOnDays(set()), PRICES).run()
    assert [(d.day, d.kind) for d in result.decisions] == [
        (MON, DecisionKind.OPENED),
        (TUE, DecisionKind.NO_ACTION),
        (WED, DecisionKind.NO_ACTION),
    ]
    assert result.decisions[1].details == ("policy proposed nothing",)
    assert len(result.still_open) == 1


def test_spread_on_the_wrong_expiry_is_blocked() -> None:
    prices = {THU: ("42.50", "12.00")}
    lots: dict[date, int | None] = {EXPIRY: 65, date(2026, 11, 9): 65}
    result = _engine(ScriptedEntry({THU}), ExitOnDays(set()), prices, lots).run([THU])
    # Thu 2026-10-29: next valid expiry is 2026-11-09; the spread is on 11-03.
    assert result.decisions[0].kind is DecisionKind.BLOCKED
    assert result.decisions[0].details[0].startswith("not_next_weeks_expiry")


def test_no_entry_expiry_means_policy_is_not_even_asked() -> None:
    day = date(2026, 11, 20)  # no known expiry 6-13 days ahead
    entry = ScriptedEntry({day})
    result = _engine(entry, ExitOnDays(set()), {day: ("10", "2")}).run([day])
    assert result.decisions[0].details == ("no entry expiry today",)
    assert entry.calls == []


def test_unknown_lot_size_blocks_fail_closed() -> None:
    result = _engine(ScriptedEntry({MON}), ExitOnDays(set()), PRICES, lots={EXPIRY: None}).run(
        [MON]
    )
    assert result.decisions[0].details == (f"lot size unknown for {EXPIRY}",)
    assert result.still_open == []


def test_hard_limits_apply_whatever_the_policy_proposes() -> None:
    entry = ScriptedEntry({MON}, delta=Decimal("0.20"))
    result = _engine(entry, ExitOnDays(set()), PRICES).run([MON])
    assert result.decisions[0].kind is DecisionKind.BLOCKED
    assert result.decisions[0].details[0].startswith("short_delta_too_high")


def test_loss_limit_hit_forces_exits_and_blocks_entries() -> None:
    crash = {MON: ("42.50", "12.00"), TUE: ("190.00", "5.00"), WED: ("190.00", "5.00")}
    exit_ = ExitOnDays(set())
    entry = ScriptedEntry({MON, WED})
    small = BacktestConfig(capital=Decimal(1_000_000), margin_available=Decimal(5_000_000))
    data = market(spread_bars(bull_put(), crash))
    engine = ReplayEngine(
        data, Strategy(entry, exit_, SettleFill()), expiry_calendar(), LOTS, small
    )
    result = engine.run()
    # Tue close: open loss (147.50 + 7) x 130 = 20,085 > 1% weekly limit (10,000) -> hit Wed.
    assert exit_.limit_flags == [False, True]
    assert result.closed[0].reasons == ("loss_limit_hit",)
    assert result.decisions[-1].kind is DecisionKind.BLOCKED
    assert result.decisions[-1].details == ("loss limit hit",)
    assert WED not in entry.calls


def test_missing_bar_for_open_leg_fails_loudly() -> None:
    prices = {MON: ("42.50", "12.00")}
    data = market(spread_bars(bull_put(), prices))
    engine = ReplayEngine(
        data,
        Strategy(ScriptedEntry({MON}), ExitOnDays(set()), SettleFill()),
        expiry_calendar(),
        LOTS,
        CONFIG,
    )
    with pytest.raises(DataError, match="no bar for open leg"):
        engine.run([MON, TUE])


def test_entry_after_the_first_day_uses_the_running_budget() -> None:
    result = _engine(ScriptedEntry({TUE}), ExitOnDays(set()), PRICES).run()
    assert [d.kind for d in result.decisions] == [
        DecisionKind.NO_ACTION,
        DecisionKind.OPENED,
        DecisionKind.NO_ACTION,
    ]
    assert result.still_open[0].entry_day == TUE

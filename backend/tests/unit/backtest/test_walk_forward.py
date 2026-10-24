"""Walk-forward: choose on past trades that had closed, score on the unseen next window."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest

from fintrade.backtest.candidates import Candidate
from fintrade.backtest.counterfactuals import CandidateOutcome, CounterfactualRun
from fintrade.backtest.trades import ClosedTrade, OpenTrade
from fintrade.backtest.walk_forward import (
    Arm,
    SearchConfig,
    Window,
    add_months,
    credit_pct_of_width,
    walk_forward,
    windows,
)
from fintrade.core.errors import InvalidInputError
from fintrade.core.instruments import Position, Structure
from tests.support.instruments import bull_put, iron_condor

START, END = date(2024, 1, 1), date(2025, 1, 1)
CONFIG = SearchConfig(train_months=6, test_months=3, min_train_trades=3)


def _outcome(
    day: date,
    net: int,
    delta: str = "0.10",
    hold_days: int = 5,
    credit: str = "20",
    position: Position | None = None,
) -> CandidateOutcome:
    pos = position or bull_put(24600, 24400)  # width 200
    prices = {leg.contract: Decimal(0) for leg in pos.legs}
    prices[pos.legs[0].contract] = Decimal(credit)
    trade = OpenTrade(1, pos, day, prices, 65, Decimal(0), Decimal(0), Decimal(1), Decimal(1))
    exit_day = day + timedelta(days=hold_days)
    closed = ClosedTrade(trade, exit_day, {}, Decimal(0), ("x",), Decimal(net))
    candidate = Candidate(pos.structure, Decimal(delta), Decimal(200), pos, {})
    return CandidateOutcome(day, candidate, closed)


def _weekly(start: date, end: date, net: int, **kw: Any) -> list[CandidateOutcome]:
    days = [start + timedelta(weeks=i) for i in range((end - start).days // 7)]
    return [_outcome(d, net, **kw) for d in days]


def _arm(delta: str, min_pct: str = "0") -> Arm:
    return Arm("base", Structure.BULL_PUT, Decimal(delta), Decimal(200), Decimal(min_pct))


def test_add_months() -> None:
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 28)
    assert add_months(date(2024, 11, 15), 3) == date(2025, 2, 15)
    assert add_months(date(2024, 3, 15), -6) == date(2023, 9, 15)


def test_windows_tile_the_test_period() -> None:
    assert windows(START, END, CONFIG) == [
        Window(date(2024, 1, 1), date(2024, 7, 1), date(2024, 10, 1)),
        Window(date(2024, 4, 1), date(2024, 10, 1), date(2025, 1, 1)),
    ]
    assert windows(START, date(2024, 8, 1), CONFIG)[-1].test_end == date(2024, 8, 1)
    assert windows(START, date(2024, 6, 1), CONFIG) == []


def test_best_training_arm_is_scored_on_the_next_window() -> None:
    good = _weekly(START, END, 500, delta="0.08")
    bad = _weekly(START, END, -100, delta="0.12")
    run = CounterfactualRun(outcomes=good + bad)
    first, second = walk_forward({"base": run}, START, END, CONFIG)
    assert first.arm == _arm("0.08")
    assert first.train_score == 500
    assert first.test
    assert all(date(2024, 7, 1) <= o.decision_day < date(2024, 10, 1) for o in first.test)
    assert second.arm == _arm("0.08")


def test_trades_still_open_at_test_start_are_not_used_for_the_choice() -> None:
    # 0.12 looks great only through one trade that closes after the test window opens
    steady = _weekly(START, END, 100, delta="0.08")
    late_win = _outcome(date(2024, 6, 28), 1_000_000, delta="0.12", hold_days=10)
    rest = _weekly(START, date(2024, 6, 1), 50, delta="0.12")
    result = walk_forward({"base": CounterfactualRun(outcomes=[*steady, late_win, *rest])},
                          START, date(2024, 10, 1), CONFIG)  # fmt: skip
    assert result[0].arm == _arm("0.08")


def test_too_few_training_trades_means_no_trading() -> None:
    sparse = [_outcome(date(2024, 2, 1), 100), _outcome(date(2024, 3, 1), 100)]
    (result,) = walk_forward({"base": CounterfactualRun(outcomes=sparse)}, START,
                             date(2024, 10, 1), CONFIG)  # fmt: skip
    assert (result.arm, result.train_score, result.test) == (None, None, ())


def test_min_credit_filter_creates_stricter_arms() -> None:
    thin = _weekly(START, END, -50, credit="8")  # 4% of width
    rich = _weekly(START + timedelta(days=1), END, 200, credit="30")  # 15% of width
    config = SearchConfig(6, 3, 3, (Decimal(0), Decimal(10)))
    result = walk_forward({"base": CounterfactualRun(outcomes=thin + rich)}, START, END, config)
    assert result[0].arm == _arm("0.10", "10")
    assert all(credit_pct_of_width(o) >= 10 for o in result[0].test)


def test_ties_resolve_the_same_way_every_time() -> None:
    a = _weekly(START, END, 100, delta="0.08")
    b = _weekly(START, END, 100, delta="0.10")
    runs = {"base": CounterfactualRun(outcomes=b + a)}
    assert walk_forward(runs, START, END, CONFIG)[0].arm == _arm("0.08")


def test_exit_configs_compete_as_separate_arms() -> None:
    runs = {
        "pt50": CounterfactualRun(outcomes=_weekly(START, END, 100)),
        "pt70": CounterfactualRun(outcomes=_weekly(START, END, 150)),
    }
    assert walk_forward(runs, START, END, CONFIG)[0].arm.exit_label == "pt70"  # type: ignore[union-attr]


def test_condor_credit_is_the_thinner_side() -> None:
    condor = iron_condor()
    outcome = _outcome(START, 0, position=condor, credit="40")  # put side 20%, call side 0%
    assert credit_pct_of_width(outcome) == 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"train_months": 0},
        {"test_months": 0},
        {"min_train_trades": 0},
        {"min_credit_pcts": ()},
        {"min_credit_pcts": (Decimal(-1),)},
        {"min_credit_pcts": (Decimal(100),)},
    ],
)
def test_invalid_search_config(kwargs: dict[str, Any]) -> None:
    with pytest.raises(InvalidInputError):
        SearchConfig(**kwargs)

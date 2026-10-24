from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from fintrade.core.rules.exits import ExitInputs, ExitReason, exit_reasons
from fintrade.core.rules.strategy_config import ExitConfig
from fintrade.core.timezone import IST
from tests.support.instruments import bull_put, iron_condor

DEADLINE = datetime(2026, 11, 2, 15, 0, tzinfo=IST)


def _inputs(**overrides: Any) -> ExitInputs:
    base = ExitInputs(
        position=iron_condor(),  # short put 24600, short call 25800
        max_profit=Decimal(7605),  # target 50% = 3802.50, stop 2x = -15210
        open_pnl=Decimal(1000),
        spot=Decimal(25200),
        now=datetime(2026, 10, 29, 11, 0, tzinfo=IST),
        exit_deadline=DEADLINE,
        loss_limit_hit=False,
    )
    return replace(base, **overrides)


def test_hold_when_nothing_applies() -> None:
    assert exit_reasons(_inputs()) == []


@pytest.mark.parametrize(("pnl", "close"), [("3802.50", True), ("3802.49", False)])
def test_profit_target_boundary(pnl: str, close: bool) -> None:
    result = exit_reasons(_inputs(open_pnl=Decimal(pnl)))
    assert result == ([ExitReason.PROFIT_TARGET] if close else [])


def test_profit_target_is_configurable() -> None:
    config = ExitConfig(profit_target_pct_of_max=Decimal(70))
    assert exit_reasons(_inputs(open_pnl=Decimal(5000)), config) == []
    assert exit_reasons(_inputs(open_pnl=Decimal("5323.50")), config) == [ExitReason.PROFIT_TARGET]


@pytest.mark.parametrize(("pnl", "close"), [("-15210", True), ("-15209.99", False)])
def test_stop_loss_at_twice_the_credit(pnl: str, close: bool) -> None:
    result = exit_reasons(_inputs(open_pnl=Decimal(pnl)))
    assert result == ([ExitReason.STOP_LOSS] if close else [])


@pytest.mark.parametrize(
    ("spot", "touched"),
    [("24600", True), ("24599", True), ("24600.05", False), ("25799.95", False), ("25800", True)],
)
def test_short_strike_touch(spot: str, touched: bool) -> None:
    result = exit_reasons(_inputs(spot=Decimal(spot)))
    assert result == ([ExitReason.STRIKE_TOUCHED] if touched else [])


def test_bull_put_only_watches_its_put_strike() -> None:
    inputs = _inputs(position=bull_put(), max_profit=Decimal(3965), spot=Decimal(30000))
    assert exit_reasons(inputs) == []


@pytest.mark.parametrize(
    ("offset", "close"), [(timedelta(0), True), (timedelta(seconds=-1), False)]
)
def test_time_exit_at_the_deadline(offset: timedelta, close: bool) -> None:
    result = exit_reasons(_inputs(now=DEADLINE + offset))
    assert result == ([ExitReason.TIME_EXIT] if close else [])


def test_loss_limit_hit_closes_everything() -> None:
    assert exit_reasons(_inputs(loss_limit_hit=True)) == [ExitReason.LOSS_LIMIT_HIT]


def test_all_applicable_reasons_reported() -> None:
    inputs = _inputs(
        open_pnl=Decimal(-20000), spot=Decimal(24500), now=DEADLINE, loss_limit_hit=True
    )
    assert exit_reasons(inputs) == [
        ExitReason.STOP_LOSS,
        ExitReason.STRIKE_TOUCHED,
        ExitReason.TIME_EXIT,
        ExitReason.LOSS_LIMIT_HIT,
    ]


def test_debit_entry_never_hits_profit_target_but_has_a_stop() -> None:
    inputs = _inputs(max_profit=Decimal(-260), open_pnl=Decimal(100))
    assert exit_reasons(inputs) == []
    assert exit_reasons(replace(inputs, open_pnl=Decimal(-520))) == [ExitReason.STOP_LOSS]


def test_zero_credit_position_never_hits_the_profit_target() -> None:
    assert exit_reasons(_inputs(max_profit=Decimal(0), open_pnl=Decimal(10))) == []


def test_small_credit_position_still_has_a_profit_target() -> None:
    inputs = _inputs(max_profit=Decimal(1), open_pnl=Decimal("0.5"))
    assert exit_reasons(inputs) == [ExitReason.PROFIT_TARGET]

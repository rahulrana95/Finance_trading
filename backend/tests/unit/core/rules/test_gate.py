from dataclasses import replace
from datetime import datetime, time, timedelta
from typing import Any

import pytest

from fintrade.core.rules.gate import GateInputs, GateRule, OrderIntent, check_gate
from fintrade.core.timezone import IST
from tests.support.rules import codes

NOW = datetime(2026, 10, 27, 10, 30, tzinfo=IST)


def _inputs(**overrides: Any) -> GateInputs:
    base = GateInputs(
        intent=OrderIntent.OPEN,
        now=NOW,
        is_trading_day=True,
        kill_switch_engaged=False,
        last_data_update=NOW - timedelta(seconds=30),
        ledger_matches_broker=True,
    )
    return replace(base, **overrides)


def test_healthy_state_allows_opening() -> None:
    assert check_gate(_inputs()) == []


def test_kill_switch_blocks_new_risk() -> None:
    assert codes(check_gate(_inputs(kill_switch_engaged=True))) == [GateRule.KILL_SWITCH]


def test_ledger_mismatch_blocks_new_risk() -> None:
    assert codes(check_gate(_inputs(ledger_matches_broker=False))) == [GateRule.LEDGER_MISMATCH]


@pytest.mark.parametrize(
    ("clock", "open_"), [((9, 14), False), ((9, 15), True), ((15, 29), True), ((15, 30), False)]
)
def test_market_hours_boundaries(clock: tuple[int, int], open_: bool) -> None:
    now = datetime.combine(NOW.date(), time(*clock), tzinfo=IST)
    result = codes(check_gate(_inputs(now=now, last_data_update=now)))
    assert result == ([] if open_ else [GateRule.MARKET_CLOSED])


def test_holiday_is_closed() -> None:
    assert codes(check_gate(_inputs(is_trading_day=False))) == [GateRule.MARKET_CLOSED]


@pytest.mark.parametrize(
    ("age", "stale"),
    [
        (timedelta(minutes=5), False),
        (timedelta(minutes=5, microseconds=1), True),
        (timedelta(seconds=-1), True),
    ],
    ids=["exactly 5 min", "just over 5 min", "from the future"],
)
def test_stale_data_boundaries(age: timedelta, stale: bool) -> None:
    result = codes(check_gate(_inputs(last_data_update=NOW - age)))
    assert result == ([GateRule.STALE_DATA] if stale else [])


def test_no_data_at_all_is_stale() -> None:
    assert codes(check_gate(_inputs(last_data_update=None))) == [GateRule.STALE_DATA]


def test_all_problems_reported_together() -> None:
    inputs = _inputs(kill_switch_engaged=True, last_data_update=None, ledger_matches_broker=False)
    assert codes(check_gate(inputs)) == [
        GateRule.KILL_SWITCH,
        GateRule.STALE_DATA,
        GateRule.LEDGER_MISMATCH,
    ]


def test_closing_is_always_allowed_even_when_everything_is_wrong() -> None:
    inputs = _inputs(
        intent=OrderIntent.CLOSE,
        kill_switch_engaged=True,
        is_trading_day=False,
        last_data_update=None,
        ledger_matches_broker=False,
    )
    assert check_gate(inputs) == []

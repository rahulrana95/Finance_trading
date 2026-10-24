"""Violation details are part of the audit log (AGENTS.md section 6), so their exact text
is checked. This also lets mutation testing catch a blanked or altered message."""

from datetime import date, datetime, timedelta
from decimal import Decimal

from fintrade.core.bars import OptionType
from fintrade.core.instruments import Side, credit_spread
from fintrade.core.rules.entry import check_entry
from fintrade.core.rules.filters import check_filters
from fintrade.core.rules.gate import GateInputs, OrderIntent, check_gate
from fintrade.core.rules.strategy_config import EntryFilterConfig
from fintrade.core.timezone import IST
from tests.support.instruments import EXPIRY, iron_condor
from tests.support.rules import good_account, good_entry
from tests.unit.core.rules.test_filters import _inputs as filter_inputs


def _details(violations: list) -> list[str]:  # type: ignore[type-arg]
    return [str(v) for v in violations]


def test_entry_violation_details() -> None:
    condor = iron_condor()
    short_put, short_call = condor.put_spread.short.contract, condor.call_spread.short.contract
    entry = good_entry(
        condor,
        short_deltas={short_put: Decimal("0.13")},
        entry_expiry=date(2026, 11, 9),
        max_loss=Decimal(200_000),
        margin_required=Decimal(2_000_001),
    )
    account = good_account(open_positions=5, new_positions_today=1, loss_limit_hit=True)
    assert _details(check_entry(entry, account)) == [
        f"short_delta_too_high: |0.13| > 0.12 for {short_put}",
        f"short_delta_missing: no delta for {short_call}",
        f"not_next_weeks_expiry: {EXPIRY} != allowed 2026-11-09",
        "loss_limit_hit: a loss limit is hit",
        "max_loss_exceeds_budget: open + new max loss 240000 > remaining 150000",
        "too_many_open_positions: 5 open, max 5",
        "too_many_new_positions_today: 1 today, max 1",
        "margin_limit_exceeded: margin 60.00% > 60%",
    ]


def test_margin_and_underlying_details() -> None:
    entry = good_entry(margin_required=Decimal(2_000_001))
    assert _details(check_entry(entry, good_account())) == [
        "margin_limit_exceeded: margin 60.00% > 60%"
    ]
    no_margin = good_account(margin_available=Decimal(0))
    assert _details(check_entry(good_entry(), no_margin)) == [
        "margin_limit_exceeded: no margin available"
    ]
    bank = credit_spread(
        symbol="BANKNIFTY",
        expiry=EXPIRY,
        option_type=OptionType.PUT,
        short_strike=Decimal(51000),
        long_strike=Decimal(50800),
        lots=1,
    )
    assert _details(check_entry(good_entry(bank), good_account())) == [
        "underlying_not_allowed: ['BANKNIFTY'] != NIFTY"
    ]
    assert [leg.side for leg in bank.legs] == [Side.SELL, Side.BUY]


def test_filter_violation_details() -> None:
    late = filter_inputs(now=datetime(2026, 10, 27, 15, 0, tzinfo=IST))
    assert _details(check_filters(late)) == [
        "outside_entry_window: 15:00:00 not in [10:00:00, 15:00:00)"
    ]
    event = filter_inputs(event_days=frozenset({date(2026, 10, 28)}))
    assert _details(check_filters(event)) == ["event_blackout: event on 2026-10-28"]
    band = EntryFilterConfig(vix_min=Decimal(11), vix_max=Decimal(22))
    assert _details(check_filters(filter_inputs(india_vix=None), band)) == [
        "vix_missing: India VIX needed for the VIX band"
    ]
    assert _details(check_filters(filter_inputs(india_vix=Decimal(30)), band)) == [
        "vix_out_of_band: VIX 30 outside [11, 22]"
    ]


def test_gate_violation_details() -> None:
    now = datetime(2026, 10, 27, 10, 30, tzinfo=IST)
    stale = now - timedelta(minutes=6)
    inputs = GateInputs(OrderIntent.OPEN, now, True, True, stale, False)
    assert _details(check_gate(inputs)) == [
        "kill_switch_engaged: kill switch is engaged",
        f"stale_data: last update {stale}, older than 0:05:00",
        "ledger_mismatch: ledger does not match broker",
    ]
    closed = GateInputs(OrderIntent.OPEN, now, False, False, now, True)
    assert _details(check_gate(closed)) == [f"market_closed: market closed at {now}"]

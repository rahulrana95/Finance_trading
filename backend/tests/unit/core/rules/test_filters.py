from dataclasses import replace
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

import pytest

from fintrade.core.errors import InvalidInputError
from fintrade.core.rules.filters import FilterInputs, FilterRule, check_filters
from fintrade.core.rules.strategy_config import EntryFilterConfig
from fintrade.core.timezone import IST
from tests.support.calendar import trading_calendar
from tests.support.instruments import bull_put, iron_condor
from tests.support.rules import codes

TUE = date(2026, 10, 27)


def _inputs(**overrides: Any) -> FilterInputs:
    condor = iron_condor()
    prices = dict(
        zip(
            [leg.contract for leg in condor.legs],
            [Decimal("42.50"), Decimal(12), Decimal(38), Decimal(10)],
            strict=True,
        )
    )
    base = FilterInputs(
        position=condor,
        entry_prices=prices,  # put credit 30.50 (15.25%), call credit 28.00 (14%)
        now=datetime(2026, 10, 27, 10, 30, tzinfo=IST),
        india_vix=Decimal("14.5"),
        event_days=frozenset(),
        calendar=trading_calendar(),
    )
    return replace(base, **overrides)


def _at(hour: int, minute: int) -> datetime:
    return datetime.combine(TUE, time(hour, minute), tzinfo=IST)


def test_clean_inputs_pass_with_default_config() -> None:
    assert check_filters(_inputs()) == []


@pytest.mark.parametrize(
    ("hm", "allowed"), [((9, 59), False), ((10, 0), True), ((14, 59), True), ((15, 0), False)]
)
def test_entry_window_boundaries(hm: tuple[int, int], allowed: bool) -> None:
    result = codes(check_filters(_inputs(now=_at(*hm))))
    assert result == ([] if allowed else [FilterRule.OUTSIDE_ENTRY_WINDOW])


def test_entry_window_uses_ist_whatever_the_input_zone() -> None:
    assert check_filters(_inputs(now=datetime(2026, 10, 27, 4, 30, tzinfo=UTC))) == []


def test_naive_time_rejected() -> None:
    with pytest.raises(InvalidInputError):
        check_filters(_inputs(now=datetime(2026, 10, 27, 10, 30)))  # noqa: DTZ001


def test_each_condor_side_needs_the_minimum_credit() -> None:
    violations = check_filters(_inputs(), EntryFilterConfig(min_credit_pct_of_width=Decimal(15)))
    assert codes(violations) == [FilterRule.CREDIT_TOO_LOW]
    assert violations[0].detail == "bear_call credit 28 < 30 (15% of 200)"


def test_single_spread_is_checked_too() -> None:
    spread = bull_put()
    prices = {spread.short.contract: Decimal(25), spread.long.contract: Decimal(10)}  # 15 = 7.5%
    violations = check_filters(_inputs(position=spread, entry_prices=prices))
    assert codes(violations) == [FilterRule.CREDIT_TOO_LOW]


def test_credit_exactly_at_minimum_allowed() -> None:
    config = EntryFilterConfig(min_credit_pct_of_width=Decimal("14"))
    assert check_filters(_inputs(), config) == []


def test_both_sides_reported_when_both_too_low() -> None:
    config = EntryFilterConfig(min_credit_pct_of_width=Decimal(16))
    assert codes(check_filters(_inputs(), config)) == [FilterRule.CREDIT_TOO_LOW] * 2


@pytest.mark.parametrize(
    ("event", "blocked"),
    [(TUE, True), (date(2026, 10, 28), True), (date(2026, 10, 29), False)],
    ids=["today", "next trading day", "two days out"],
)
def test_event_blackout(event: date, blocked: bool) -> None:
    result = codes(check_filters(_inputs(event_days=frozenset({event}))))
    assert result == ([FilterRule.EVENT_BLACKOUT] if blocked else [])


def test_weekend_event_before_next_trading_day_blocks_friday_entry() -> None:
    friday = datetime(2026, 10, 23, 11, 0, tzinfo=IST)
    inputs = _inputs(now=friday, event_days=frozenset({date(2026, 10, 24)}))
    assert codes(check_filters(inputs)) == [FilterRule.EVENT_BLACKOUT]


def test_event_blackout_can_be_disabled() -> None:
    inputs = _inputs(event_days=frozenset({TUE}))
    assert check_filters(inputs, EntryFilterConfig(event_blackout=False)) == []


BAND = EntryFilterConfig(vix_min=Decimal(11), vix_max=Decimal(22))


@pytest.mark.parametrize(
    ("vix", "blocked"), [("11", False), ("22", False), ("10.99", True), ("22.01", True)]
)
def test_vix_band_boundaries(vix: str, blocked: bool) -> None:
    result = codes(check_filters(_inputs(india_vix=Decimal(vix)), BAND))
    assert result == ([FilterRule.VIX_OUT_OF_BAND] if blocked else [])


@pytest.mark.parametrize("vix", [None, Decimal("NaN")])
def test_vix_needed_when_band_is_set(vix: Decimal | None) -> None:
    assert codes(check_filters(_inputs(india_vix=vix), BAND)) == [FilterRule.VIX_MISSING]


def test_vix_not_needed_when_band_is_off() -> None:
    assert check_filters(_inputs(india_vix=None)) == []


def test_only_a_minimum_vix() -> None:
    config = EntryFilterConfig(vix_min=Decimal(12))
    assert codes(check_filters(_inputs(india_vix=Decimal(11)), config)) == [
        FilterRule.VIX_OUT_OF_BAND
    ]
    assert check_filters(_inputs(india_vix=Decimal(40)), config) == []

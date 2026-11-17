"""The stock table service (S01-S03) and its pure row builder."""

from datetime import UTC, date, datetime, timedelta

import pytest

from steady.adapters.seed import load_seed_stocks
from steady.constants import (
    NEED_FRESH_PRICES,
    NEED_LOT_SIZE,
    NEED_OFFICIAL_PRICES,
    NEED_PRICE_HISTORY,
)
from steady.services.stocks import StockNotFoundError, StockService, build_view
from tests.support import FakePrices, closes

TODAY = date(2026, 11, 17)
NOW = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
SEEDS = load_seed_stocks()
ICICI, NESTLE = SEEDS[0], SEEDS[1]
SLIDE = closes([100.0] * 60 + [95.0, 90.0, 85.0])


def test_a_row_carries_price_zone_recovery_and_scores():
    view = build_view(NESTLE, SLIDE, FakePrices(), TODAY)
    assert (view.last_price, view.reference_high, view.below_high_pct, view.zone) == (
        85.0,
        100.0,
        15.0,
        1,
    )
    assert view.price_as_of == "2026-11-17"
    assert (view.falls10, view.recovered12m_pct, view.longest_recovery_days) == (1, 0, 1)
    assert view.max_drawdown_pct == -15
    assert view.history[-1] == 85.0
    assert view.price_source == "Fake prices"
    assert 0 < view.evidence < 100


def test_needs_list_what_is_missing():
    view = build_view(NESTLE, SLIDE, FakePrices(), TODAY)
    assert NEED_OFFICIAL_PRICES in view.needs
    assert NEED_LOT_SIZE in view.needs
    assert "Net profit for FY2023" in view.needs
    assert "Fewer than 8 years of price history" in view.needs
    assert NEED_FRESH_PRICES not in view.needs


def test_an_official_source_and_a_known_lot_size_ask_for_less():
    view = build_view(ICICI, SLIDE, FakePrices(official=True), TODAY)
    assert NEED_OFFICIAL_PRICES not in view.needs
    assert NEED_LOT_SIZE not in view.needs
    assert view.data_quality == 80  # only the short history counts against it


def test_old_prices_are_flagged_and_cost_data_quality():
    fresh = build_view(ICICI, SLIDE, FakePrices(official=True), TODAY)
    stale = build_view(ICICI, SLIDE, FakePrices(official=True), TODAY + timedelta(days=5))
    assert NEED_FRESH_PRICES in stale.needs
    assert stale.data_quality == fresh.data_quality - 20


@pytest.mark.parametrize("series", [None, [], closes([100.0] * 59)])
def test_without_enough_prices_the_row_says_so_and_shows_zeros(series):
    view = build_view(NESTLE, series, FakePrices(), TODAY)
    assert view.needs[0] == NEED_PRICE_HISTORY
    assert (view.last_price, view.zone, view.stability, view.price_as_of) == (0.0, 0, 0, "")
    assert view.financial > 0


def test_metrics_only_count_falls_from_2016():
    early = closes([100.0] * 60 + [80.0, 100.0] + [100.0] * 200, end=date(2016, 3, 1))
    late = closes([100.0] * 300, end=TODAY)
    view = build_view(ICICI, early + late, FakePrices(), TODAY)
    assert view.falls10 == 0


def test_lists_every_stock_and_fetches_each_once():  # S01
    prices = FakePrices(default=SLIDE)
    service = StockService(SEEDS, prices, lambda: NOW)
    assert [v.seed.symbol for v in service.list_stocks()] == [s.symbol for s in SEEDS]
    assert sorted(prices.calls) == sorted(s.symbol for s in SEEDS)


def test_one_failing_stock_does_not_break_the_rest():  # S02
    service = StockService(SEEDS, FakePrices({"TITAN": None}, default=SLIDE), lambda: NOW)
    views = {v.seed.symbol: v for v in service.list_stocks()}
    assert views["TITAN"].needs[0] == NEED_PRICE_HISTORY
    assert views["MARICO"].last_price == 85.0


def test_bad_prices_are_treated_as_missing():
    service = StockService(
        SEEDS, FakePrices({"TITAN": closes([100.0] * 60 + [-1.0])}, default=SLIDE), lambda: NOW
    )
    assert service.get_stock("TITAN").needs[0] == NEED_PRICE_HISTORY


def test_prices_are_cached_until_the_ttl_passes():  # S03
    now = NOW
    prices = FakePrices(default=SLIDE)
    service = StockService(SEEDS, prices, lambda: now)
    service.list_stocks()
    service.get_stock("TITAN")
    assert len(prices.calls) == 12
    now = NOW + timedelta(seconds=1799)
    service.list_stocks()
    assert len(prices.calls) == 12
    now = NOW + timedelta(seconds=1800)
    service.list_stocks()
    assert len(prices.calls) == 24


def test_get_is_case_insensitive_and_unknown_symbols_fail():
    service = StockService(SEEDS, FakePrices(default=SLIDE), lambda: NOW)
    assert service.get_stock("titan").seed.name == "Titan"
    with pytest.raises(StockNotFoundError):
        service.get_stock("NOPE")

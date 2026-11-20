"""The screener service: which stocks are in a deep fall, and the odds from past falls."""

from datetime import UTC, datetime, timedelta

import pytest

from steady.adapters.memory import MemoryStore
from steady.domain import Close, Listing
from steady.ports import PriceSourceError
from steady.services.screener import ScreenerService, check_stock
from tests.support import FakePrices, closes

NOW = datetime(2026, 11, 17, 13, 0, tzinfo=UTC)
FLAT = closes([100.0] * 400)
# A finished fall (30% down, back up) and then a fresh 25% fall on the last day.
FELL = closes([100.0] * 130 + [70.0] + [84.0] * 126 + [91.0] * 130 + [100.0] * 12 + [75.0])
SHORT = closes([100.0] * 50)
A, B, C = (
    Listing("AAA", "Alpha", "Banks"),
    Listing("BBB", "Beta", "IT"),
    Listing("CCC", "Gamma", "Auto"),
)


def clock() -> datetime:
    return NOW


def make(data: dict[str, list[Close] | None], universe=(A, B, C), store: MemoryStore | None = None):
    prices = FakePrices({"^NSEI": FLAT, **data}, default=FLAT)
    return ScreenerService(list(universe), prices, store or MemoryStore(), clock, lambda: "s1")


def test_a_stock_in_a_deep_fall_gets_a_row_with_its_own_record():
    events, row = check_stock(A, FELL, {})
    assert row is not None
    assert (row.symbol, row.name, row.industry) == ("AAA", "Alpha", "Banks")
    assert (row.last_price, row.year_high, row.below_pct, row.level) == (75.0, 100.0, 25.0, 25.0)
    assert row.price_as_of == "2026-11-17"
    assert row.worst_day_pct == 25.0
    assert (row.own_falls, row.own_falls_with_year, row.own_higher_after_year) == (1, 1, 1)
    assert {e.level for e in events} == {20.0, 25.0, 30.0}


def test_no_row_when_not_in_a_fall_or_without_enough_history():
    assert check_stock(A, FLAT, {})[1] is None
    assert check_stock(A, SHORT, {}) == ([], None)


def test_the_market_state_is_read_by_date():
    day = FELL[130].day
    events, _ = check_stock(A, FELL, {day: 12.0})
    assert {e.market for e in events} == {"down"}


def test_a_screen_lists_fallen_stocks_deepest_first_with_the_odds_table():
    deeper = closes([100.0] * 399 + [55.0])
    state = make({"AAA": FELL, "CCC": deeper}).run()
    screen = state.screen
    assert (state.running, state.error) == (False, None)
    assert screen is not None
    assert (screen.id, screen.created_at, screen.universe, screen.priced) == ("s1", NOW, 3, 3)
    assert (screen.market_below_pct, screen.market) == (0.0, "fine")
    assert [(r.symbol, r.level) for r in screen.rows] == [("CCC", 40.0), ("AAA", 25.0)]
    odds = {(o.level, o.market): o for o in screen.odds}
    assert (odds[25.0, "fine"].events, odds[25.0, "fine"].higher_12m_pct) == (1, 100.0)
    assert odds[25.0, "deep"].events == 0
    assert {r.confidence for r in screen.rows} == {"low"}
    first = screen.rows[1].evidence
    assert [e.met for e in first] == [False, False, True, True, True]
    assert (
        first[0].detail == "Nifty is 0.0% below its 1-year high; a market-wide fall starts at 10%."
    )
    assert first[2].detail == "It is 25.0% below its 1-year high of 100."
    assert first[4].detail == (
        "1 past falls like this: 100% were higher after 6 months, 100% after a year, "
        "and 0% fell another 20% first."
    )
    assert screen.rows[0].evidence[4].detail == "No past fall like this to compare with."


def test_a_falling_market_is_flagged():
    market = closes([100.0] * 399 + [88.0])
    state = make({"^NSEI": market, "AAA": FELL}).run()
    assert state.screen is not None
    assert (state.screen.market_below_pct, state.screen.market) == (12.0, "down")
    assert [r.confidence for r in state.screen.rows] == ["medium"]


def test_a_deep_market_fall_makes_fallen_stocks_high_confidence_first():
    market = closes([100.0] * 399 + [80.0])
    shallow = closes([100.0] * 399 + [79.0])
    state = make({"^NSEI": market, "AAA": shallow, "BBB": FELL}).run()
    assert state.screen is not None
    assert state.screen.market == "deep"
    assert [(r.symbol, r.confidence) for r in state.screen.rows] == [
        ("BBB", "high"),
        ("AAA", "medium"),
    ]
    assert [e.met for e in state.screen.rows[0].evidence][:4] == [True, True, True, True]


def test_a_stock_without_prices_is_skipped():
    state = make({"BBB": None, "AAA": FELL}).run()
    assert state.screen is not None
    assert (state.screen.universe, state.screen.priced) == (3, 2)


def test_no_prices_at_all_is_an_error_and_keeps_the_last_screen():
    store = MemoryStore()
    make({"AAA": FELL}, store=store).run()
    state = make({"AAA": None, "BBB": None, "CCC": None}, store=store).run()
    assert state.error == "The price source did not answer for any stock."
    assert state.screen is not None  # the earlier one
    assert state.running is False


def test_a_missing_market_index_is_an_error():
    assert make({"^NSEI": None}).run().error == "no prices for ^NSEI"


def test_an_unexpected_failure_is_reported_without_details(monkeypatch: pytest.MonkeyPatch):
    service = make({})

    def boom() -> None:
        raise RuntimeError("secret detail")

    monkeypatch.setattr(service, "_screen", boom)
    state = service.run()
    assert (state.error, state.running, state.screen) == ("The screen failed.", False, None)


def test_only_one_screen_runs_at_a_time():
    service = make({})
    assert service.start() is True
    assert service.state().running is True
    assert service.start() is False
    assert service.run().screen is None  # left alone while the first is going
    service.execute()
    assert service.state().running is False
    assert service.start() is True


def test_a_new_error_free_start_clears_the_old_error():
    service = make({"^NSEI": None})
    assert service.run().error is not None
    service.start()
    assert service.state().error is None


def test_a_recent_screen_is_not_repeated_but_an_old_one_is():
    store = MemoryStore()
    assert make({}, store=store).run_if_stale() is True
    assert make({}, store=store).run_if_stale() is False
    later = ScreenerService(
        [A], FakePrices(default=FLAT), store, lambda: NOW + timedelta(hours=21), lambda: "s2"
    )
    assert later.run_if_stale() is True
    assert store.latest_screen().id == "s2"  # type: ignore[union-attr]


def test_ids_are_unique_by_default():
    service = ScreenerService([A], FakePrices(default=FLAT), MemoryStore(), clock)
    first = service.run().screen
    second = service.run().screen
    assert first is not None
    assert second is not None
    assert first.id != second.id


def test_the_fake_reports_a_missing_symbol():
    with pytest.raises(PriceSourceError):
        FakePrices({"X": None}).daily_closes("X")

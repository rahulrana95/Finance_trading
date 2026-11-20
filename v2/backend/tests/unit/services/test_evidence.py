"""The plain-word reasons behind a confidence."""

from steady.core.screen import Odds
from steady.domain import ScreenRow
from steady.services.evidence import build_evidence

GOOD = Odds(30.0, "deep", 914, 86.0, 66.0, 85.0, 852, 69.0, 93.0, 35.0)


def row(below: float, high: float, level: float, worst_day: float) -> ScreenRow:
    return ScreenRow(
        "X", "X", "X", 1.0, "2026-11-17", high, below, level, 0, 0, 0, worst_day, "", ()
    )


WEAK = Odds(30.0, "fine", 1335, 72.0, 51.0, 54.0, 1187, 52.0, 53.0, 56.0)


def test_everything_in_favour():
    items = build_evidence(row(32.4, 1250.0, 30.0, 6.2), "deep", 17.3, GOOD)
    assert [e.met for e in items] == [True, True, True, True, True]
    assert [e.label for e in items] == [
        "The whole market is in a fall",
        "The market fall is deep (15% or more)",
        "The stock has fallen 25% or more",
        "No sign of a demerger or split",
        "Similar falls usually ended higher",
    ]
    assert (
        items[0].detail == "Nifty is 17.3% below its 1-year high; a market-wide fall starts at 10%."
    )
    assert items[2].detail == "It is 32.4% below its 1-year high of 1,250."
    assert items[3].detail == "Its biggest one-day drop in the last year was 6%."
    assert items[4].detail == (
        "914 past falls like this: 85% were higher after 6 months, 93% after a year, "
        "and 35% fell another 20% first."
    )


def test_a_stock_that_fell_alone_and_looks_like_a_demerger():
    items = build_evidence(row(22.0, 500.0, 20.0, 62.0), "fine", 2.0, WEAK)
    assert [e.met for e in items] == [False, False, False, False, False]


def test_a_market_fall_that_is_not_deep():
    assert [e.met for e in build_evidence(row(26.0, 500.0, 25.0, 5.0), "down", 11.0, GOOD)][:2] == [
        True,
        False,
    ]


def test_without_past_falls_there_is_nothing_to_compare():
    empty = Odds(40.0, "deep", 0, 0.0, 0.0, 0.0, 0, 0.0, 0.0, 0.0)
    for odds in (None, empty):
        last = build_evidence(row(45.0, 500.0, 40.0, 5.0), "deep", 16.0, odds)[4]
        assert (last.met, last.detail) == (False, "No past fall like this to compare with.")

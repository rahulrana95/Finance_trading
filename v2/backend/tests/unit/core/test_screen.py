"""Falls from the 1-year high and the odds table built from them."""

import pytest

from steady.core.screen import (
    DipEvent,
    below_high_series,
    confidence,
    dip_events,
    level_reached,
    market_state,
    odds_table,
    worst_day_pct,
)

# 130 flat days, a 30% drop, six months 20% above the low, then 130 days 30% above it.
STORY = [100.0] * 130 + [70.0] + [84.0] * 126 + [91.0] * 130
NO_MARKET_FALL = ["fine"] * len(STORY)


def test_depth_needs_history_and_uses_the_highest_recent_close():
    depths = below_high_series([100.0] * 119 + [90.0, 110.0, 99.0])
    assert depths[:119] == [None] * 119
    assert depths[119] == pytest.approx(10.0)
    assert depths[120] == 0.0
    assert depths[121] == pytest.approx(10.0)


def test_an_old_high_drops_out_of_the_one_year_window():
    depths = below_high_series([200.0] + [100.0] * 252, window=252, min_history=1)
    assert depths[251] == pytest.approx(50.0)
    assert depths[252] == 0.0


@pytest.mark.parametrize(
    ("below", "level"), [(0, 0), (19.9, 0), (20, 20), (27, 25), (33, 30), (80, 40)]
)
def test_the_deepest_level_reached(below: float, level: float):
    assert level_reached(below) == level


def test_a_fall_is_recorded_once_per_level_with_what_followed():
    events = dip_events(STORY, NO_MARKET_FALL)
    assert [(e.index, e.level) for e in events] == [(130, 20.0), (130, 25.0), (130, 30.0)]
    first = events[0]
    assert [first.best_6m, first.end_6m] == pytest.approx([20.0, 20.0])
    assert [first.best_12m, first.end_12m, first.worst_12m] == pytest.approx([30.0, 30.0, 20.0])
    assert first.market == "fine"


def test_the_market_state_on_the_day_is_kept():
    flags = ["fine"] * 130 + ["deep"] + ["fine"] * 256
    assert {e.market for e in dip_events(STORY, flags)} == {"deep"}


def test_a_fall_with_six_months_but_not_a_year_has_no_year_result():
    events = dip_events(STORY[:300], NO_MARKET_FALL[:300])
    assert events[0].end_6m == pytest.approx(20.0)
    assert (events[0].best_12m, events[0].end_12m, events[0].worst_12m) == (None, None, None)


def test_a_fall_too_recent_to_judge_is_left_out():
    assert dip_events(STORY[:200], NO_MARKET_FALL[:200]) == []


def test_a_second_fall_counts_only_after_the_stock_came_back_near_its_high():
    still_down = [100.0] * 130 + [70.0] + [72.0] * 100 + [65.0] + [72.0] * 130
    assert [
        e.index for e in dip_events(still_down, ["fine"] * len(still_down)) if e.level == 20
    ] == [130]
    recovered = [100.0] * 130 + [70.0] + [95.0] * 60 + [70.0] + [80.0] * 130
    again = [e.index for e in dip_events(recovered, ["fine"] * len(recovered)) if e.level == 20]
    assert again == [130, 191]


def test_a_fall_that_lasts_over_a_year_counts_again():
    long_fall = [100.0] * 130 + [70.0] + [79.0] * 252 + [50.0] + [60.0] * 130
    indexes = [e.index for e in dip_events(long_fall, ["fine"] * len(long_fall)) if e.level == 20]
    assert indexes == [130, 383]


def event(
    level: float, down: str, best6: float, end6: float, year: tuple[float, float, float] | None
):
    best12, end12, worst12 = year or (None, None, None)
    return DipEvent(0, level, down, best6, end6, best12, end12, worst12)


def test_the_odds_table_counts_each_outcome():
    events = [
        event(25, "deep", 25, 12, (40, 35, -5)),
        event(25, "deep", 12, -3, (10, -8, -30)),
        event(25, "deep", 5, 2, None),
        event(25, "fine", 9, -1, (5, -20, -25)),
    ]
    table = {(o.level, o.market): o for o in odds_table(events)}
    assert len(table) == 12
    down = table[25.0, "deep"]
    assert (down.events, down.events_12m) == (3, 2)
    assert (down.gain10_6m_pct, down.gain20_6m_pct, down.higher_6m_pct) == (66.7, 33.3, 66.7)
    assert (down.gain30_12m_pct, down.higher_12m_pct, down.fell_further_12m_pct) == (
        50.0,
        50.0,
        50.0,
    )
    alone = table[25.0, "fine"]
    assert (alone.events, alone.higher_6m_pct, alone.fell_further_12m_pct) == (1, 0.0, 100.0)


def test_a_group_with_no_falls_shows_zeros():
    empty = odds_table([])[0]
    assert (empty.events, empty.events_12m, empty.higher_6m_pct, empty.higher_12m_pct) == (
        0,
        0,
        0.0,
        0.0,
    )


def test_the_biggest_one_day_drop_in_the_last_year():
    assert worst_day_pct([100.0, 50.0, 55.0, 44.0]) == 50.0
    assert worst_day_pct([100.0, 50.0] + [50.0] * 252) == 0.0  # the drop is older than a year
    assert worst_day_pct([100.0, 101.0]) == 0.0
    assert worst_day_pct([100.0]) == 0.0


@pytest.mark.parametrize(
    ("below", "state"),
    [(0, "fine"), (9.9, "fine"), (10, "down"), (14.9, "down"), (15, "deep"), (40, "deep")],
)
def test_the_market_has_three_states(below: float, state: str):
    assert market_state(below) == state


@pytest.mark.parametrize(
    ("level", "market", "worst_day", "expected"),
    [
        (25, "deep", 8, "high"),
        (40, "deep", 8, "high"),
        (20, "deep", 8, "medium"),
        (40, "down", 8, "medium"),
        (40, "fine", 8, "low"),
        (40, "deep", 35, "low"),  # looks like a demerger, not a fall
    ],
)
def test_confidence_is_high_only_in_a_deep_market_fall(
    level: float, market: str, worst_day: float, expected: str
):
    assert confidence(level, market, worst_day) == expected

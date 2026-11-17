"""Metrics from daily closes (TEST_PLAN M01-M17)."""

import json
import math
from datetime import date
from pathlib import Path

import pytest

from steady.core.metrics import (
    below_high_pct,
    fall_events,
    history_years,
    max_drawdown_pct,
    recovery_stats,
    reference_high,
    validate_closes,
)

FIXTURE = Path(__file__).parents[2] / "fixtures" / "icici_closes.json"


def flat(n: int, value: float = 100.0) -> list[float]:
    return [value] * n


def test_reference_high_of_a_rising_series_is_the_last_close():  # M01
    closes = [float(i) for i in range(1, 127)]
    assert reference_high(closes) == 126.0


def test_reference_high_ignores_a_peak_older_than_the_window():  # M02
    closes = [500.0, *flat(130)]
    assert reference_high(closes) == 100.0


def test_reference_high_needs_enough_history():  # M03
    assert reference_high(flat(59)) is None
    assert reference_high(flat(60)) == 100.0


def test_below_high_is_zero_at_or_above_the_high():
    assert below_high_pct(110.0, 100.0) == 0.0
    assert below_high_pct(1297.8, 1540.0) == pytest.approx(15.727, abs=0.001)


def test_a_close_exactly_ten_percent_below_counts_as_a_fall():  # M04
    events = fall_events([*flat(60), 90.0], pct=10.0)
    assert len(events) == 1
    assert events[0].start == 60


def test_a_close_just_under_ten_percent_below_is_not_a_fall():  # M05
    assert fall_events([*flat(60), 90.01], pct=10.0) == []


def test_a_fall_ends_when_the_close_is_back_at_the_old_high():  # M06
    events = fall_events([*flat(60), 90.0, 95.0, 100.0, 101.0], pct=10.0)
    assert [(e.recovery_days, e.open_days) for e in events] == [(2, 0)]


def test_a_fall_that_never_recovers_stays_open():  # M07
    events = fall_events([*flat(60), 90.0, 85.0, 88.0], pct=10.0)
    assert [(e.recovery_days, e.open_days) for e in events] == [(None, 2)]
    assert events[0].depth_pct == pytest.approx(15.0)


def test_two_separate_falls_are_two_events():  # M08
    closes = [*flat(60), 90.0, 100.0, *flat(5), 89.0, 100.0]
    assert [e.start for e in fall_events(closes, pct=10.0)] == [60, 67]


def test_a_deeper_fall_inside_an_open_event_is_the_same_event():  # M09
    events = fall_events([*flat(60), 90.0, 70.0, 100.0], pct=10.0)
    assert len(events) == 1
    assert events[0].depth_pct == pytest.approx(30.0)


def test_events_can_start_from_a_later_index():
    closes = [*flat(60), 90.0, 100.0, *flat(5), 89.0, 100.0]
    assert [e.start for e in fall_events(closes, pct=10.0, start_index=65)] == [67]


def test_recovery_share_counts_only_quick_recoveries():  # M10
    closes = [*flat(60), 90.0, 100.0, 90.0, *flat(300, 95.0), 100.0]
    stats = recovery_stats(fall_events(closes, pct=10.0), within_days=252)
    assert stats.count == 2
    assert stats.recovered_within_pct == 50.0
    assert stats.longest_days == 301
    assert stats.open_days == 0


def test_recovery_share_is_unknown_without_falls():  # M11
    stats = recovery_stats([])
    assert stats.count == 0
    assert stats.recovered_within_pct is None
    assert stats.longest_days == 0


def test_an_open_fall_counts_towards_the_longest_time():
    stats = recovery_stats(fall_events([*flat(60), 90.0, 85.0, 88.0], pct=10.0))
    assert (stats.longest_days, stats.open_days, stats.recovered_within_pct) == (2, 2, 0.0)


def test_max_drawdown_on_a_known_series():  # M12
    assert max_drawdown_pct([100.0, 120.0, 60.0, 90.0, 130.0, 117.0]) == pytest.approx(50.0)


def test_a_flat_series_has_no_drawdown_or_events():  # M13
    assert max_drawdown_pct(flat(200)) == 0.0
    assert fall_events(flat(200), pct=10.0) == []


def test_history_years_from_dates():
    assert history_years([date(2016, 1, 1), date(2026, 1, 1)]) == pytest.approx(10.0, abs=0.01)
    assert history_years([]) == 0.0


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf])
def test_bad_prices_are_rejected(bad: float):  # M15
    with pytest.raises(ValueError, match="positive"):
        validate_closes([100.0, bad])


def test_good_prices_pass_validation():
    validate_closes([100.0, 101.5])


def test_icici_bank_matches_the_research():  # M17
    rows = json.loads(FIXTURE.read_text())
    dates = [date.fromisoformat(d) for d, _ in rows]
    closes = [c for _, c in rows]
    start = next(i for i, d in enumerate(dates) if d >= date(2016, 1, 1))
    stats = recovery_stats(fall_events(closes, pct=10.0, start_index=start))
    assert stats.count == 11
    assert round(stats.recovered_within_pct or 0) == 91
    assert stats.longest_days == 343
    assert stats.open_days == 0
    assert round(max_drawdown_pct(closes[start:])) == 48

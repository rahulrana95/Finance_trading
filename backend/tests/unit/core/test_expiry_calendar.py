from datetime import date, datetime

import pytest

from fintrade.core.calendar import MAX_DAYS_TO_EXPIRY_AT_ENTRY, ExpiryCalendar
from fintrade.core.errors import InvalidInputError
from fintrade.core.timezone import IST
from tests.support.calendar import expiry_calendar, trading_calendar


def test_max_days_is_min_days_plus_one_week() -> None:
    assert MAX_DAYS_TO_EXPIRY_AT_ENTRY == 13


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 10, 26), date(2026, 11, 3)),  # Mon: 8 days
        (date(2026, 10, 27), date(2026, 11, 3)),  # expiry day itself: 7 days
        (date(2026, 10, 28), date(2026, 11, 3)),  # exactly 6 days: allowed
        (date(2026, 10, 29), date(2026, 11, 9)),  # 5 days is too close; shifted Monday expiry
        (date(2026, 10, 14), date(2026, 10, 27)),  # 2026-10-19 is only 5 days away
    ],
)
def test_entry_expiry_is_next_weeks_expiry(today: date, expected: date) -> None:
    assert expiry_calendar().entry_expiry(today) == expected


def test_entry_expiry_boundary_13_and_14_days() -> None:
    cal = ExpiryCalendar([date(2026, 10, 27)], trading_calendar())
    assert cal.entry_expiry(date(2026, 10, 14)) == date(2026, 10, 27)  # 13 days
    assert cal.entry_expiry(date(2026, 10, 13)) is None  # 14 days


def test_no_entry_after_last_known_expiry() -> None:
    assert expiry_calendar().entry_expiry(date(2026, 11, 20)) is None


@pytest.mark.parametrize(
    ("expiry", "deadline_day"),
    [
        (date(2026, 11, 3), date(2026, 11, 2)),  # Tue expiry -> Mon
        (date(2026, 10, 19), date(2026, 10, 16)),  # shifted Monday expiry -> Friday
        (date(2026, 10, 6), date(2026, 10, 5)),
    ],
)
def test_exit_deadline_is_15_00_on_previous_trading_day(expiry: date, deadline_day: date) -> None:
    deadline = expiry_calendar().exit_deadline(expiry)
    expected = datetime(deadline_day.year, deadline_day.month, deadline_day.day, 15, 0, tzinfo=IST)
    assert deadline == expected


def test_exit_deadline_skips_a_holiday_before_expiry() -> None:
    cal = ExpiryCalendar([date(2026, 10, 21)], trading_calendar())  # 2026-10-20 is a holiday
    assert cal.exit_deadline(date(2026, 10, 21)).date() == date(2026, 10, 19)


def test_exit_deadline_for_unknown_expiry_rejected() -> None:
    with pytest.raises(InvalidInputError, match="not a known expiry"):
        expiry_calendar().exit_deadline(date(2026, 10, 28))

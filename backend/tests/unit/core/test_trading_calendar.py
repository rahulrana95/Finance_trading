from datetime import date

import pytest

from fintrade.core.calendar import TradingCalendar
from fintrade.core.errors import DataError, InvalidInputError
from tests.support.calendar import trading_calendar


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 10, 1), True),
        (date(2026, 10, 2), False),  # Gandhi Jayanti
        (date(2026, 10, 3), False),  # Saturday
        (date(2026, 10, 20), False),  # Dussehra
        (date(2026, 10, 21), True),
    ],
)
def test_is_trading_day(day: date, expected: bool) -> None:
    assert trading_calendar().is_trading_day(day) is expected


def test_previous_and_next_skip_holidays_and_weekends() -> None:
    cal = trading_calendar()
    assert cal.previous_trading_day(date(2026, 10, 21)) == date(2026, 10, 19)
    assert cal.next_trading_day(date(2026, 10, 1)) == date(2026, 10, 5)
    assert cal.previous_trading_day(date(2026, 10, 3)) == date(2026, 10, 1)  # from a Saturday


def test_trading_days_between_is_half_open() -> None:
    cal = trading_calendar()
    assert cal.trading_days_between(date(2026, 10, 16), date(2026, 10, 21)) == 2  # 19, 21
    assert cal.trading_days_between(date(2026, 10, 21), date(2026, 10, 21)) == 0


def test_trading_days_between_rejects_reversed_range() -> None:
    with pytest.raises(InvalidInputError, match="after end"):
        trading_calendar().trading_days_between(date(2026, 10, 22), date(2026, 10, 21))


@pytest.mark.parametrize("day", [date(2026, 9, 30), date(2026, 12, 1)])
def test_days_outside_coverage_raise_instead_of_guessing(day: date) -> None:
    cal = trading_calendar()
    with pytest.raises(DataError, match="outside calendar"):
        cal.is_trading_day(day)


def test_no_trading_day_before_first_or_after_last() -> None:
    cal = trading_calendar()
    with pytest.raises(DataError, match="no trading day before"):
        cal.previous_trading_day(cal.first_day)
    with pytest.raises(DataError, match="no trading day after"):
        cal.next_trading_day(cal.last_day)


def test_bounds_and_empty_calendar() -> None:
    cal = trading_calendar()
    assert (cal.first_day, cal.last_day) == (date(2026, 10, 1), date(2026, 11, 30))
    with pytest.raises(InvalidInputError, match="at least one trading day"):
        TradingCalendar([])

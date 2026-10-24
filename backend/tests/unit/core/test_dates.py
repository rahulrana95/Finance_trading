from datetime import date

import pytest

from fintrade.core.dates import weekdays
from fintrade.core.errors import InvalidInputError


def test_weekdays_skip_weekend() -> None:
    # Fri 2026-10-23 .. Tue 2026-10-27
    assert list(weekdays(date(2026, 10, 23), date(2026, 10, 27))) == [
        date(2026, 10, 23),
        date(2026, 10, 26),
        date(2026, 10, 27),
    ]


def test_single_weekday_and_single_weekend_day() -> None:
    assert list(weekdays(date(2026, 10, 26), date(2026, 10, 26))) == [date(2026, 10, 26)]
    assert list(weekdays(date(2026, 10, 25), date(2026, 10, 25))) == []


def test_start_after_end_rejected() -> None:
    with pytest.raises(InvalidInputError, match="after end"):
        list(weekdays(date(2026, 10, 27), date(2026, 10, 26)))

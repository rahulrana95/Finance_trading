"""Market hours in India time (09:15 to 15:30, Monday to Friday)."""

from datetime import UTC, datetime

import pytest

from steady.core.calendar import is_market_open


@pytest.mark.parametrize(
    ("utc", "expected"),
    [
        (datetime(2026, 11, 17, 3, 44, tzinfo=UTC), False),  # Tue 09:14 IST
        (datetime(2026, 11, 17, 3, 45, tzinfo=UTC), True),  # Tue 09:15 IST
        (datetime(2026, 11, 17, 7, 0, tzinfo=UTC), True),  # Tue 12:30 IST
        (datetime(2026, 11, 17, 10, 0, tzinfo=UTC), True),  # Tue 15:30 IST
        (datetime(2026, 11, 17, 10, 1, tzinfo=UTC), False),  # Tue 15:31 IST
        (datetime(2026, 11, 21, 7, 0, tzinfo=UTC), False),  # Saturday
        (datetime(2026, 11, 22, 7, 0, tzinfo=UTC), False),  # Sunday
        (datetime(2026, 11, 22, 22, 30, tzinfo=UTC), False),  # Mon 04:00 IST
    ],
)
def test_open_only_in_market_hours(utc: datetime, expected: bool):
    assert is_market_open(utc) is expected

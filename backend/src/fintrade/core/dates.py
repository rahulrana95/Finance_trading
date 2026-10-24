"""Pure date helpers."""

from collections.abc import Iterator
from datetime import date, timedelta

from fintrade.core.errors import InvalidInputError

SATURDAY = 5  # date.weekday(): Monday = 0 ... Sunday = 6


def weekdays(start: date, end: date) -> Iterator[date]:
    """Yield Monday-Friday dates from `start` to `end`, both inclusive.

    Exchange holidays are not removed here; callers handle "no data that day".
    """
    if start > end:
        raise InvalidInputError(f"start {start} is after end {end}")
    day = start
    while day <= end:
        if day.weekday() < SATURDAY:
            yield day
        day += timedelta(days=1)

"""Time source, so tests can fix the clock."""

from collections.abc import Callable
from datetime import UTC, datetime

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)

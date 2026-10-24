from datetime import UTC, datetime, timedelta

import pytest

from fintrade.core.errors import InvalidInputError
from fintrade.core.timezone import IST
from fintrade.ports.clock import Clock
from tests.support.clock import FixedClock


def test_fixed_clock_returns_ist_and_advances() -> None:
    clock: Clock = FixedClock(datetime(2026, 10, 27, 4, 30, tzinfo=UTC))
    assert clock.now() == datetime(2026, 10, 27, 10, 0, tzinfo=IST)
    assert isinstance(clock, FixedClock)
    clock.advance(timedelta(minutes=30))
    assert clock.now() == datetime(2026, 10, 27, 10, 30, tzinfo=IST)


def test_fixed_clock_rejects_naive_time() -> None:
    with pytest.raises(InvalidInputError):
        FixedClock(datetime(2026, 10, 27, 10, 0))  # noqa: DTZ001 - testing the rejection

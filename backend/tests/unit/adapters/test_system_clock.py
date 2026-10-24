from datetime import timedelta

import time_machine

from fintrade.adapters.system_clock import SystemClock
from fintrade.core.timezone import IST


@time_machine.travel("2026-10-27 04:30:00+00:00", tick=False)
def test_system_clock_returns_aware_ist_now() -> None:
    now = SystemClock().now()
    assert now.tzinfo is IST
    assert now.utcoffset() == timedelta(hours=5, minutes=30)
    assert (now.hour, now.minute) == (10, 0)

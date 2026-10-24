"""FixedClock: inject a known time in tests."""

from datetime import datetime, timedelta

from fintrade.core.timezone import ensure_ist


class FixedClock:
    def __init__(self, moment: datetime) -> None:
        self._moment = ensure_ist(moment)

    def now(self) -> datetime:
        return self._moment

    def advance(self, delta: timedelta) -> None:
        self._moment = self._moment + delta

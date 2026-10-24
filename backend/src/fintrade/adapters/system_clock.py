"""Real clock, used only at the edges of the system."""

from datetime import datetime

from fintrade.core.timezone import IST


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(tz=IST)

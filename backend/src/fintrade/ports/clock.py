"""Clock port. Logic receives time from a Clock; it never reads the system clock."""

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Current time, timezone-aware, in IST."""
        ...

"""All times are timezone-aware and expressed in IST (ENGINEERING.md section 5)."""

from datetime import datetime
from zoneinfo import ZoneInfo

from fintrade.core.errors import InvalidInputError

IST = ZoneInfo("Asia/Kolkata")


def ensure_ist(moment: datetime) -> datetime:
    """Return `moment` converted to IST. Naive datetimes are rejected, never guessed."""
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise InvalidInputError(f"naive datetime not allowed: {moment.isoformat()}")
    return moment.astimezone(IST)

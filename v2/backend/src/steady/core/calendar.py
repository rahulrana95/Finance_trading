"""Market hours. Exchange holidays are not known yet, so a holiday counts as open."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

from steady.constants import MARKET_CLOSE, MARKET_OPEN, MARKET_TIMEZONE

SATURDAY = 5


def is_market_open(now: datetime) -> bool:
    local = now.astimezone(ZoneInfo(MARKET_TIMEZONE))
    return local.weekday() < SATURDAY and time(*MARKET_OPEN) <= local.time() <= time(*MARKET_CLOSE)

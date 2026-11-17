"""Daily closes from Yahoo Finance's public chart endpoint (unofficial stopgap)."""

from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any

import httpx2 as httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from steady.clock import Clock
from steady.constants import (
    MARKET_UTC_OFFSET_MINUTES,
    PRICE_FETCH_ATTEMPTS,
    PRICE_HISTORY_START,
    YAHOO_NAME,
    YAHOO_TIMEOUT_SECONDS,
    YAHOO_URL,
    YAHOO_USER_AGENT,
)
from steady.domain import Close
from steady.ports import PriceSourceError

MARKET_TZ = timezone(timedelta(minutes=MARKET_UTC_OFFSET_MINUTES))


def new_client() -> httpx.Client:
    return httpx.Client(timeout=YAHOO_TIMEOUT_SECONDS, headers={"User-Agent": YAHOO_USER_AGENT})


def parse_chart(payload: Any) -> list[Close]:  # noqa: ANN401 - JSON from outside
    """Turns the chart JSON into closes, skipping empty rows and repeated days."""
    try:
        result = payload["chart"]["result"][0]
        pairs = zip(result["timestamp"], result["indicators"]["quote"][0]["close"], strict=True)
        by_day: dict[date, float] = {}
        for stamp, close in pairs:
            if close is not None:
                by_day[datetime.fromtimestamp(stamp, MARKET_TZ).date()] = float(close)
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise PriceSourceError("Unexpected response from the price source") from error
    if not by_day:
        raise PriceSourceError("The price source returned no prices")
    return [Close(day, close) for day, close in sorted(by_day.items())]


class YahooPriceSource:
    name = YAHOO_NAME
    official = False

    def __init__(self, client: httpx.Client, clock: Clock) -> None:
        self._client = client
        self._clock = clock

    @retry(
        stop=stop_after_attempt(PRICE_FETCH_ATTEMPTS),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def _fetch(self, symbol: str) -> Any:  # noqa: ANN401 - JSON from outside
        start = datetime.fromisoformat(PRICE_HISTORY_START).replace(tzinfo=UTC)
        response = self._client.get(
            YAHOO_URL.format(symbol=symbol),
            params={
                "period1": int(start.timestamp()),
                "period2": int((self._clock() + timedelta(days=1)).timestamp()),
                "interval": "1d",
            },
        )
        response.raise_for_status()
        return response.json()

    def daily_closes(self, symbol: str) -> list[Close]:
        try:
            return parse_chart(self._fetch(symbol))
        except (httpx.HTTPError, ValueError) as error:
            raise PriceSourceError(f"Could not fetch prices for {symbol}") from error

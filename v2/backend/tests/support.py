"""Fakes and builders shared by tests."""

from datetime import date, timedelta

from steady.domain import Close
from steady.ports import PriceSourceError


def closes(prices: list[float], end: date = date(2026, 11, 17)) -> list[Close]:
    """Consecutive calendar days ending on `end`."""
    start = end - timedelta(days=len(prices) - 1)
    return [Close(start + timedelta(days=i), p) for i, p in enumerate(prices)]


class FakePrices:
    """A price source with fixed answers. A symbol mapped to None fails."""

    def __init__(
        self,
        data: dict[str, list[Close] | None] | None = None,
        default: list[Close] | None = None,
        official: bool = False,
    ) -> None:
        self.name = "Fake prices"
        self.official = official
        self.calls: list[str] = []
        self._data = data or {}
        self._default = default

    def daily_closes(self, symbol: str) -> list[Close]:
        self.calls.append(symbol)
        answer = self._data.get(symbol, self._default)
        if answer is None:
            raise PriceSourceError(f"no prices for {symbol}")
        return answer

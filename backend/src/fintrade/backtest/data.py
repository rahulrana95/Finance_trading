"""Market data for the replay engine, with a hard guard against look-ahead.

AGENTS.md section 5: a decision on day D may only use data available on day D.
`GuardedMarketData` raises if anything asks for a later day.
"""

from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from typing import Protocol

from fintrade.core.bars import DailyContractBar
from fintrade.core.errors import DataError
from fintrade.core.instruments import OptionContract

type DayBars = Mapping[OptionContract, DailyContractBar]


class LookAheadError(DataError):
    """Something asked for data from the future. Always a bug."""


class MarketData(Protocol):
    def trading_days(self) -> Sequence[date]: ...

    def option_bars(self, day: date) -> DayBars: ...


def option_contract(bar: DailyContractBar) -> OptionContract:
    if bar.strike is None or bar.option_type is None:
        raise DataError(f"not an option bar: {bar.symbol} {bar.kind} {bar.expiry}")
    return OptionContract(bar.symbol, bar.expiry, bar.strike, bar.option_type)


class InMemoryMarketData:
    """Option bars held in memory, indexed by day."""

    def __init__(self, bars: Iterable[DailyContractBar]) -> None:
        by_day: dict[date, dict[OptionContract, DailyContractBar]] = {}
        for bar in bars:
            if bar.strike is None:
                continue  # futures are not traded by the engine
            by_day.setdefault(bar.trade_date, {})[option_contract(bar)] = bar
        self._by_day = by_day

    def trading_days(self) -> Sequence[date]:
        return sorted(self._by_day)

    def option_bars(self, day: date) -> DayBars:
        return self._by_day.get(day, {})


class GuardedMarketData:
    """Wraps a source; data after the current replay day is unreachable."""

    def __init__(self, source: MarketData) -> None:
        self._source = source
        self._current: date | None = None

    def advance_to(self, day: date) -> None:
        if self._current is not None and day <= self._current:
            raise DataError(f"replay must move forward: {day} after {self._current}")
        self._current = day

    def trading_days(self) -> Sequence[date]:
        return self._source.trading_days()

    def option_bars(self, day: date) -> DayBars:
        if self._current is None or day > self._current:
            raise LookAheadError(f"asked for {day} while replaying {self._current}")
        return self._source.option_bars(day)

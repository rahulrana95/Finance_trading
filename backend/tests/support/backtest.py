"""Fakes for engine tests: a tiny market, settle-price fills, scripted policies."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from fintrade.backtest.data import DayBars, InMemoryMarketData
from fintrade.backtest.engine import EntryProposal
from fintrade.backtest.trades import ClosedTrade, OpenTrade
from fintrade.core.bars import DailyContractBar
from fintrade.core.instruments import CreditSpread, Side
from tests.support.bars import make_bar
from tests.support.instruments import bull_put


class SettleFill:
    """Fills at settle price. Test-only: real backtests must model bid/ask (AGENTS.md §5)."""

    def fill(self, bar: DailyContractBar, order_side: Side) -> Decimal:
        return bar.settle


def spread_bars(
    spread: CreditSpread, prices: Mapping[date, tuple[str, str]]
) -> list[DailyContractBar]:
    """Bars for both legs of `spread` on each day: (short settle, long settle)."""
    bars = []
    for day, (short_px, long_px) in prices.items():
        for leg, px in ((spread.short, short_px), (spread.long, long_px)):
            c = leg.contract
            bars.append(
                make_bar(
                    trade_date=day,
                    expiry=c.expiry,
                    strike=c.strike,
                    option_type=c.option_type,
                    settle=Decimal(px),
                    close=Decimal(px),
                    open=Decimal(px),
                    high=Decimal(px),
                    low=Decimal(px),
                )
            )
    return bars


def market(bars: Iterable[DailyContractBar]) -> InMemoryMarketData:
    return InMemoryMarketData(bars)


@dataclass
class ScriptedEntry:
    """Proposes `spread` on the given days, with the given short delta."""

    days: set[date]
    spread: CreditSpread = field(default_factory=bull_put)
    delta: Decimal = Decimal("0.10")
    calls: list[date] = field(default_factory=list)

    def propose(self, day: date, bars: DayBars, expiry: date) -> EntryProposal | None:
        self.calls.append(day)
        if day not in self.days:
            return None
        return EntryProposal(
            self.spread, {self.spread.short.contract: self.delta}, Decimal(100_000)
        )


@dataclass
class ExitOnDays:
    """Exits every open trade on the given days; records the loss-limit flag it saw."""

    days: set[date]
    limit_flags: list[bool] = field(default_factory=list)

    def reasons(
        self, trade: OpenTrade, day: date, bars: DayBars, loss_limit_hit: bool
    ) -> list[str]:
        self.limit_flags.append(loss_limit_hit)
        if loss_limit_hit:
            return ["loss_limit_hit"]
        return ["scripted"] if day in self.days else []


def closed_with_pnl(gross: Decimal, costs: Decimal) -> ClosedTrade:
    """A closed trade with this gross P&L, paying `costs` on entry and again on exit."""
    spread = bull_put()
    day = date(2026, 10, 26)
    trade = OpenTrade(1, spread, day, {}, 65, Decimal(0), costs, Decimal(1), Decimal(1))
    return ClosedTrade(trade, day, {}, costs, ("scripted",), gross)

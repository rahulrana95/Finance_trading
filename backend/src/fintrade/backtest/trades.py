"""Opening, valuing and closing one simulated trade. Shared by the replay engine and the
counterfactual simulator, so both price trades identically."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from fintrade.backtest.data import DayBars
from fintrade.core.bars import DailyContractBar
from fintrade.core.charges import order_charges
from fintrade.core.errors import DataError
from fintrade.core.instruments import Leg, Position, Side
from fintrade.core.money import Rupees
from fintrade.core.pnl import Prices, mark_to_market, risk


class FillModel(Protocol):
    def fill(self, bar: DailyContractBar, order_side: Side) -> Rupees:
        """Price per unit for an order on `bar`: BUY pays, SELL receives."""
        ...


@dataclass(frozen=True, slots=True)
class OpenTrade:
    trade_id: int
    position: Position
    entry_day: date
    entry_prices: Prices
    lot_size: int
    margin: Rupees
    entry_costs: Rupees
    max_profit: Rupees
    max_loss: Rupees


@dataclass(frozen=True, slots=True)
class ClosedTrade:
    trade: OpenTrade
    exit_day: date
    exit_prices: Prices
    exit_costs: Rupees
    reasons: tuple[str, ...]
    gross_pnl: Rupees

    @property
    def net_pnl(self) -> Rupees:
        return self.gross_pnl - self.trade.entry_costs - self.exit_costs


@dataclass(frozen=True, slots=True)
class Ticket:
    """What to open: the position, its id, lot size and the margin it blocks."""

    trade_id: int
    position: Position
    lot_size: int
    margin: Rupees


def open_trade(ticket: Ticket, day: date, bars: DayBars, fills: FillModel) -> OpenTrade:
    """The trade as it would be filled today. Nothing is booked until the caller keeps it."""
    position, lot_size = ticket.position, ticket.lot_size
    prices = {leg.contract: fills.fill(leg_bar(bars, leg), leg.side) for leg in position.legs}
    position_risk = risk(position, prices, lot_size)
    return OpenTrade(
        ticket.trade_id,
        position,
        day,
        prices,
        lot_size,
        ticket.margin,
        _costs(position, prices, lot_size, day, opening=True),
        position_risk.max_profit,
        position_risk.max_loss,
    )


def close_trade(
    trade: OpenTrade, day: date, bars: DayBars, fills: FillModel, reasons: list[str]
) -> ClosedTrade:
    position = trade.position
    prices = {
        leg.contract: fills.fill(leg_bar(bars, leg), opposite(leg.side)) for leg in position.legs
    }
    gross = mark_to_market(position, trade.entry_prices, prices, trade.lot_size)
    costs = _costs(position, prices, trade.lot_size, day, opening=False)
    return ClosedTrade(trade, day, prices, costs, tuple(reasons), gross)


def settle_pnl(trade: OpenTrade, bars: DayBars) -> Rupees:
    """Mark-to-market at settle prices, before charges."""
    marks = {leg.contract: leg_bar(bars, leg).settle for leg in trade.position.legs}
    return mark_to_market(trade.position, trade.entry_prices, marks, trade.lot_size)


def opposite(side: Side) -> Side:
    return Side.SELL if side is Side.BUY else Side.BUY


def leg_bar(bars: DayBars, leg: Leg) -> DailyContractBar:
    bar = bars.get(leg.contract)
    if bar is None:
        raise DataError(f"no bar for open leg {leg.contract}")
    return bar


def _costs(position: Position, prices: Prices, lot: int, day: date, *, opening: bool) -> Rupees:
    total = Decimal(0)
    for leg in position.legs:
        side = leg.side if opening else opposite(leg.side)
        total += order_charges(side, prices[leg.contract], leg.lots * lot, day).total
    return total

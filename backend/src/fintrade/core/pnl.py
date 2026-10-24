"""Credit, max profit, max loss and mark-to-market P&L for our defined-risk positions.

All amounts are rupees (Decimal), before charges; charges are added by the caller from
`core.charges`. Max loss is the worst case at expiry: width minus credit, and for an iron
condor only one side can finish in the money, so the wider side counts.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from fintrade.core.errors import DataError, InvalidInputError
from fintrade.core.instruments import CreditSpread, Leg, OptionContract, Position, Side
from fintrade.core.money import Rupees

type Prices = Mapping[OptionContract, Rupees]


@dataclass(frozen=True, slots=True)
class PositionRisk:
    credit_points: Rupees  # net premium received per unit
    max_profit: Rupees
    max_loss: Rupees


def _price(prices: Prices, leg: Leg) -> Rupees:
    try:
        value = prices[leg.contract]
    except KeyError as exc:
        raise DataError(f"no price for {leg.contract}") from exc
    if not value.is_finite() or value < 0:
        raise DataError(f"invalid price {value} for {leg.contract}")
    return value


def _units(position: Position, lot_size: int) -> int:
    if isinstance(lot_size, bool) or not isinstance(lot_size, int) or lot_size <= 0:
        raise InvalidInputError(f"lot size must be a positive int: {lot_size!r}")
    return position.lots * lot_size


def credit_points(position: Position, entry: Prices) -> Rupees:
    """Premium received minus premium paid, per unit."""
    return sum(
        (_price(entry, leg) * (1 if leg.side is Side.SELL else -1) for leg in position.legs),
        start=Decimal(0),
    )


def risk(position: Position, entry: Prices, lot_size: int) -> PositionRisk:
    units = _units(position, lot_size)
    credit = credit_points(position, entry)
    width = _max_width(position)
    loss_points = width - credit
    if loss_points < 0:
        raise DataError(f"credit {credit} exceeds width {width}: entry prices are impossible")
    return PositionRisk(
        credit_points=credit, max_profit=credit * units, max_loss=loss_points * units
    )


def _max_width(position: Position) -> Rupees:
    if isinstance(position, CreditSpread):
        return position.width
    return max(position.put_spread.width, position.call_spread.width)


def mark_to_market(position: Position, entry: Prices, current: Prices, lot_size: int) -> Rupees:
    """Open P&L before charges: what closing every leg at `current` would realise."""
    units = _units(position, lot_size)
    total = Decimal(0)
    for leg in position.legs:
        change = _price(current, leg) - _price(entry, leg)
        total += -change if leg.side is Side.SELL else change
    return total * units


@dataclass(frozen=True, slots=True)
class OpenPosition:
    position: Position
    entry: Prices
    lot_size: int


def portfolio_max_loss(positions: Iterable[OpenPosition]) -> Rupees:
    """Sum of worst cases. Compared against the remaining monthly loss budget
    (AGENTS.md section 1)."""
    return sum(
        (risk(p.position, p.entry, p.lot_size).max_loss for p in positions), start=Decimal(0)
    )


def portfolio_mark_to_market(positions: Iterable[OpenPosition], current: Prices) -> Rupees:
    return sum(
        (mark_to_market(p.position, p.entry, current, p.lot_size) for p in positions),
        start=Decimal(0),
    )

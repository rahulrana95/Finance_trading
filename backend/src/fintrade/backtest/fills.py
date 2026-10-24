"""Fill simulator for daily bars (AGENTS.md section 5: never fill at mid or last alone).

NSE bhavcopy has no bid/ask, so a fill is the reference price moved against us by a
modelled half-spread plus slippage, then rounded to the tick against us:
BUY pays more, SELL receives less (never below zero).

The default spread numbers are conservative placeholders. T4.7c calibrates the spread
model against recorded live quotes; it plugs in through `SpreadModel`.
"""

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from enum import StrEnum
from typing import Protocol

from fintrade.core.bars import DailyContractBar
from fintrade.core.errors import DataError, InvalidInputError
from fintrade.core.instruments import Side
from fintrade.core.money import Rupees

_ZERO = Decimal(0)
_PCT = Decimal(100)


class PriceBasis(StrEnum):
    SETTLE = "settle"
    CLOSE = "close"
    WORST = "worst"  # BUY from the higher of close/settle, SELL from the lower


@dataclass(frozen=True, slots=True)
class FillConfig:
    basis: PriceBasis = PriceBasis.WORST
    tick_size: Rupees = Decimal("0.05")  # NSE index options tick
    slippage_ticks: int = 1  # beyond the half-spread, per order

    def __post_init__(self) -> None:
        if not self.tick_size.is_finite() or self.tick_size <= 0:
            raise InvalidInputError(f"tick size must be positive: {self.tick_size}")
        if self.slippage_ticks < 0:
            raise InvalidInputError(f"slippage ticks must be >= 0: {self.slippage_ticks}")


class SpreadModel(Protocol):
    def half_spread(self, bar: DailyContractBar, reference: Rupees, tick: Rupees) -> Rupees:
        """Modelled distance from mid to the touch for `bar`, in rupees per unit."""
        ...


@dataclass(frozen=True, slots=True)
class ProportionalSpread:
    """Half-spread = a percent of the price, but at least a number of ticks."""

    half_spread_pct: Decimal = Decimal("2.5")
    min_half_spread_ticks: int = 2

    def __post_init__(self) -> None:
        pct = self.half_spread_pct
        if not pct.is_finite() or not _ZERO <= pct < _PCT:
            raise InvalidInputError(f"half spread pct must be in [0, 100): {pct}")
        if self.min_half_spread_ticks < 0:
            raise InvalidInputError(
                f"min half spread ticks must be >= 0: {self.min_half_spread_ticks}"
            )

    def half_spread(self, bar: DailyContractBar, reference: Rupees, tick: Rupees) -> Rupees:
        return max(reference * self.half_spread_pct / _PCT, tick * self.min_half_spread_ticks)


def fill_price(
    reference: Rupees, order_side: Side, *, half_spread: Rupees, config: FillConfig
) -> Rupees:
    """Price per unit for an order: reference moved against us, rounded to tick against us."""
    if not reference.is_finite() or reference <= 0:  # finite first: comparing NaN raises
        raise DataError(f"reference price must be positive: {reference}")
    if half_spread < 0:
        raise InvalidInputError(f"half spread must be >= 0: {half_spread}")
    cost = half_spread + config.tick_size * config.slippage_ticks
    tick = config.tick_size
    if order_side is Side.BUY:
        return ((reference + cost) / tick).to_integral_value(ROUND_CEILING) * tick
    raw = ((reference - cost) / tick).to_integral_value(ROUND_FLOOR) * tick
    return max(raw, _ZERO)


class BarFillModel:
    """`FillModel` for the replay engine, from daily bars."""

    def __init__(self, config: FillConfig, spread: SpreadModel) -> None:
        self._config = config
        self._spread = spread

    def fill(self, bar: DailyContractBar, order_side: Side) -> Rupees:
        reference = self._reference(bar, order_side)
        half = self._spread.half_spread(bar, reference, self._config.tick_size)
        return fill_price(reference, order_side, half_spread=half, config=self._config)

    def _reference(self, bar: DailyContractBar, order_side: Side) -> Rupees:
        basis = self._config.basis
        if basis is PriceBasis.SETTLE:
            return bar.settle
        if basis is PriceBasis.CLOSE:
            return bar.close
        worse = max if order_side is Side.BUY else min
        return worse(bar.settle, bar.close)

"""Candidate trades for one day: every structure x target delta x width the config allows.

Daily bars are end-of-day, so a daily backtest decides and fills at the close: Greeks are
measured from settle prices with time to expiry from `decision_time` on the day.

Short strike for a target delta: the out-of-the-money strike with the largest |delta|
that does not exceed the target (so never above the AGENTS.md limit). The hedge sits
`width` points further out and must have a bar today. Combinations that cannot be built
from today's chain are simply absent; nothing is guessed.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

from fintrade.backtest.data import DayBars
from fintrade.core.bars import OptionType
from fintrade.core.errors import InvalidInputError
from fintrade.core.instruments import (
    CreditSpread,
    IronCondor,
    OptionContract,
    Position,
    Structure,
    credit_spread,
)
from fintrade.core.limits import HARD_LIMITS
from fintrade.core.pricing.black76 import EXPIRY_CLOSE, time_to_expiry_years
from fintrade.core.pricing.chain import ChainGreeks, ChainPoint, chain_greeks
from fintrade.core.timezone import IST

_SPREAD_TYPE = {Structure.BULL_PUT: OptionType.PUT, Structure.BEAR_CALL: OptionType.CALL}


@dataclass(frozen=True, slots=True)
class CandidateConfig:
    """Search grid. Values are placeholders; the walk-forward search (T4.6) sets them."""

    structures: tuple[Structure, ...] = tuple(Structure)
    target_deltas: tuple[Decimal, ...] = (Decimal("0.08"), Decimal("0.10"), Decimal("0.12"))
    widths: tuple[Decimal, ...] = (Decimal(100), Decimal(200), Decimal(300))
    lots: int = 1
    rate: float = 0.065  # annual risk-free rate; deltas barely move with it
    min_price: Decimal = Decimal("0.05")  # one tick: below this no IV is trusted
    decision_time: time = EXPIRY_CLOSE  # end-of-day bars: decide at the close

    def __post_init__(self) -> None:
        if not self.structures or not self.target_deltas or not self.widths:
            raise InvalidInputError("structures, target deltas and widths must be non-empty")
        limit = HARD_LIMITS.max_short_delta
        if any(not (0 < d <= limit) for d in self.target_deltas):
            raise InvalidInputError(f"target deltas must be in (0, {limit}]: {self.target_deltas}")
        if any(w <= 0 for w in self.widths):
            raise InvalidInputError(f"widths must be positive: {self.widths}")
        if self.lots < 1:
            raise InvalidInputError(f"lots must be >= 1: {self.lots}")
        if not math.isfinite(self.rate) or self.min_price <= 0:
            raise InvalidInputError("rate must be finite and min price positive")


@dataclass(frozen=True, slots=True)
class Candidate:
    structure: Structure
    target_delta: Decimal
    width: Decimal
    position: Position
    short_deltas: Mapping[OptionContract, Decimal]  # |delta| of each short leg


def generate_candidates(
    day: date, bars: DayBars, expiry: date, config: CandidateConfig
) -> list[Candidate]:
    points = _chain_points(bars, expiry)
    if not points:
        return []
    now = datetime.combine(day, config.decision_time, tzinfo=IST)
    years = time_to_expiry_years(now, expiry)
    chain = chain_greeks(list(points.values()), years, config.rate, config.min_price)
    builder = _Builder(chain, points, expiry, config.lots)
    found: list[Candidate] = []
    for structure in config.structures:
        for target in config.target_deltas:
            for width in config.widths:
                candidate = builder.build(structure, target, width)
                if candidate is not None:
                    found.append(candidate)
    return found


def _chain_points(bars: DayBars, expiry: date) -> dict[Decimal, ChainPoint]:
    prices: dict[Decimal, dict[OptionType, Decimal]] = {}
    for contract, bar in bars.items():
        if contract.expiry == expiry and contract.symbol == HARD_LIMITS.underlying:
            prices.setdefault(contract.strike, {})[contract.option_type] = bar.settle
    return {
        strike: ChainPoint(strike, by_type.get(OptionType.CALL), by_type.get(OptionType.PUT))
        for strike, by_type in sorted(prices.items())
    }


@dataclass(frozen=True, slots=True)
class _Side:
    spread: CreditSpread
    short_delta: Decimal


class _Builder:
    def __init__(
        self, chain: ChainGreeks, points: Mapping[Decimal, ChainPoint], expiry: date, lots: int
    ) -> None:
        self._chain = chain
        self._points = points
        self._expiry = expiry
        self._lots = lots

    def build(self, structure: Structure, target: Decimal, width: Decimal) -> Candidate | None:
        if structure is Structure.IRON_CONDOR:
            put = self._side(OptionType.PUT, target, width)
            call = self._side(OptionType.CALL, target, width)
            if put is None or call is None:
                return None
            condor = IronCondor(put.spread, call.spread)
            deltas = {put.spread.short.contract: put.short_delta}
            deltas[call.spread.short.contract] = call.short_delta
            return Candidate(structure, target, width, condor, deltas)
        side = self._side(_SPREAD_TYPE[structure], target, width)
        if side is None:
            return None
        deltas = {side.spread.short.contract: side.short_delta}
        return Candidate(structure, target, width, side.spread, deltas)

    def _side(self, option_type: OptionType, target: Decimal, width: Decimal) -> _Side | None:
        short = self._short_strike(option_type, target)
        if short is None:
            return None
        strike, delta = short
        hedge = strike - width if option_type is OptionType.PUT else strike + width
        point = self._points.get(hedge)
        if point is None or (point.put if option_type is OptionType.PUT else point.call) is None:
            return None
        spread = credit_spread(
            symbol=HARD_LIMITS.underlying,
            expiry=self._expiry,
            option_type=option_type,
            short_strike=strike,
            long_strike=hedge,
            lots=self._lots,
        )
        return _Side(spread, delta)

    def _short_strike(
        self, option_type: OptionType, target: Decimal
    ) -> tuple[Decimal, Decimal] | None:
        forward = self._chain.forward
        best: tuple[Decimal, Decimal] | None = None
        for strike, strike_greeks in self._chain.by_strike.items():
            otm = strike < forward if option_type is OptionType.PUT else strike > forward
            delta = Decimal(abs(strike_greeks.of(option_type).delta))  # exact, no rounding
            if otm and delta <= target and (best is None or delta > best[1]):
                best = (strike, delta)
        return best

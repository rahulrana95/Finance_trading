"""Greeks for every strike of one expiry's chain, from market prices.

Steps: forward from put-call parity (pricing.forward), then one IV per strike from its
out-of-the-money side (calls at or above the forward, puts below), then call and put
Greeks at that IV. Strikes whose OTM price is below `min_price` (sub-tick, no time
value worth trusting) or has no IV are left out rather than guessed.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from fintrade.core.bars import OptionType
from fintrade.core.pricing.black76 import Greeks, greeks, implied_vol
from fintrade.core.pricing.forward import StrikeQuote, forward_from_chain


@dataclass(frozen=True, slots=True)
class ChainPoint:
    """Reference prices at one strike; None when that option has no price."""

    strike: Decimal
    call: Decimal | None
    put: Decimal | None


@dataclass(frozen=True, slots=True)
class StrikeGreeks:
    strike: Decimal
    iv: float
    call: Greeks
    put: Greeks

    def of(self, option_type: OptionType) -> Greeks:
        return self.call if option_type is OptionType.CALL else self.put


@dataclass(frozen=True, slots=True)
class ChainGreeks:
    forward: float
    by_strike: Mapping[Decimal, StrikeGreeks]


def chain_greeks(
    points: Sequence[ChainPoint], years: float, rate: float, min_price: Decimal
) -> ChainGreeks:
    quotes = [
        StrikeQuote(float(p.strike), float(p.call), float(p.put))
        for p in points
        if p.call is not None and p.put is not None
    ]
    forward = forward_from_chain(quotes, years, rate)
    by_strike: dict[Decimal, StrikeGreeks] = {}
    for point in points:
        strike = float(point.strike)
        otm_type = OptionType.CALL if strike >= forward else OptionType.PUT
        otm_price = point.call if otm_type is OptionType.CALL else point.put
        if otm_price is None or otm_price < min_price:
            continue
        vol = implied_vol(float(otm_price), otm_type, forward, strike, years, rate)
        if vol is None:
            continue
        by_strike[point.strike] = StrikeGreeks(
            point.strike,
            vol,
            greeks(OptionType.CALL, forward, strike, years, rate, vol),
            greeks(OptionType.PUT, forward, strike, years, rate, vol),
        )
    return ChainGreeks(forward, by_strike)

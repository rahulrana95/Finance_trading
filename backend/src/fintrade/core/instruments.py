"""Option contracts, legs and the defined-risk structures we trade (AGENTS.md section 1).

Construction validates the structure, so an invalid spread (naked short, hedge on the
wrong side, mismatched expiry or size) cannot exist as an object.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from fintrade.core.bars import OptionType
from fintrade.core.errors import InvalidInputError


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class Structure(StrEnum):
    BULL_PUT = "bull_put"
    BEAR_CALL = "bear_call"
    IRON_CONDOR = "iron_condor"


@dataclass(frozen=True, slots=True)
class OptionContract:
    symbol: str
    expiry: date
    strike: Decimal
    option_type: OptionType

    def __post_init__(self) -> None:
        if not self.symbol:
            raise InvalidInputError("symbol is empty")
        if not self.strike.is_finite() or self.strike <= 0:
            raise InvalidInputError(f"strike must be positive: {self.strike}")


@dataclass(frozen=True, slots=True)
class Leg:
    contract: OptionContract
    side: Side
    lots: int

    def __post_init__(self) -> None:
        if isinstance(self.lots, bool) or not isinstance(self.lots, int) or self.lots <= 0:
            raise InvalidInputError(f"lots must be a positive int: {self.lots!r}")


@dataclass(frozen=True, slots=True)
class CreditSpread:
    """One short option hedged by a long option further out of the money."""

    short: Leg
    long: Leg

    def __post_init__(self) -> None:
        short, long = self.short, self.long
        if short.side is not Side.SELL or long.side is not Side.BUY:
            raise InvalidInputError("credit spread needs a SELL short leg and a BUY long leg")
        if short.contract.symbol != long.contract.symbol:
            raise InvalidInputError("legs must be on the same underlying")
        if short.contract.expiry != long.contract.expiry:
            raise InvalidInputError("hedge must have the same expiry as the short leg")
        if short.contract.option_type is not long.contract.option_type:
            raise InvalidInputError("legs must both be calls or both be puts")
        if short.lots != long.lots:
            raise InvalidInputError("hedge must cover the short leg lot for lot")
        if self.width <= 0:
            raise InvalidInputError("hedge must be further out of the money than the short leg")

    @property
    def option_type(self) -> OptionType:
        return self.short.contract.option_type

    @property
    def structure(self) -> Structure:
        return Structure.BULL_PUT if self.option_type is OptionType.PUT else Structure.BEAR_CALL

    @property
    def width(self) -> Decimal:
        """Distance between strikes, positive when the hedge is on the correct side."""
        gap = self.long.contract.strike - self.short.contract.strike
        return gap if self.option_type is OptionType.CALL else -gap

    @property
    def expiry(self) -> date:
        return self.short.contract.expiry

    @property
    def lots(self) -> int:
        return self.short.lots

    @property
    def legs(self) -> tuple[Leg, Leg]:
        return (self.short, self.long)


@dataclass(frozen=True, slots=True)
class IronCondor:
    """A bull put spread below the market and a bear call spread above it."""

    put_spread: CreditSpread
    call_spread: CreditSpread

    def __post_init__(self) -> None:
        if self.put_spread.structure is not Structure.BULL_PUT:
            raise InvalidInputError("put side must be a bull put spread")
        if self.call_spread.structure is not Structure.BEAR_CALL:
            raise InvalidInputError("call side must be a bear call spread")
        if self.put_spread.expiry != self.call_spread.expiry:
            raise InvalidInputError("both sides must share one expiry")
        if self.put_spread.lots != self.call_spread.lots:
            raise InvalidInputError("both sides must have the same lots")
        if self.put_spread.short.contract.strike >= self.call_spread.short.contract.strike:
            raise InvalidInputError("short put strike must be below short call strike")

    @property
    def structure(self) -> Structure:
        return Structure.IRON_CONDOR

    @property
    def expiry(self) -> date:
        return self.put_spread.expiry

    @property
    def lots(self) -> int:
        return self.put_spread.lots

    @property
    def legs(self) -> tuple[Leg, Leg, Leg, Leg]:
        return (*self.put_spread.legs, *self.call_spread.legs)


type Position = CreditSpread | IronCondor


def credit_spread(
    *,
    symbol: str,
    expiry: date,
    option_type: OptionType,
    short_strike: Decimal,
    long_strike: Decimal,
    lots: int,
) -> CreditSpread:
    """Convenience builder for the common case."""
    return CreditSpread(
        short=Leg(OptionContract(symbol, expiry, short_strike, option_type), Side.SELL, lots),
        long=Leg(OptionContract(symbol, expiry, long_strike, option_type), Side.BUY, lots),
    )

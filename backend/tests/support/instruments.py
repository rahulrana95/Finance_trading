"""Factories for spreads and iron condors (Nifty ~25,200, next week's expiry)."""

from datetime import date
from decimal import Decimal

from fintrade.core.bars import OptionType
from fintrade.core.instruments import CreditSpread, IronCondor, credit_spread

EXPIRY = date(2026, 11, 3)


def bull_put(short: int = 24600, long: int = 24400, lots: int = 2) -> CreditSpread:
    return credit_spread(
        symbol="NIFTY",
        expiry=EXPIRY,
        option_type=OptionType.PUT,
        short_strike=Decimal(short),
        long_strike=Decimal(long),
        lots=lots,
    )


def bear_call(short: int = 25800, long: int = 26000, lots: int = 2) -> CreditSpread:
    return credit_spread(
        symbol="NIFTY",
        expiry=EXPIRY,
        option_type=OptionType.CALL,
        short_strike=Decimal(short),
        long_strike=Decimal(long),
        lots=lots,
    )


def iron_condor(lots: int = 2) -> IronCondor:
    return IronCondor(put_spread=bull_put(lots=lots), call_spread=bear_call(lots=lots))

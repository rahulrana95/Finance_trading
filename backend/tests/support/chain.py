"""Synthetic option chains priced with Black-76 at a flat volatility."""

from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from fintrade.backtest.data import DayBars, option_contract
from fintrade.core.bars import OptionType
from fintrade.core.pricing.black76 import price
from fintrade.core.pricing.chain import ChainPoint
from tests.support.bars import make_bar

FORWARD, YEARS, RATE, VOL = 25213.4, 8 / 365, 0.065, 0.13


def _px(option_type: OptionType, forward: float, strike: int, vol: float) -> Decimal:
    return Decimal(str(round(price(option_type, forward, float(strike), YEARS, RATE, vol), 4)))


def flat_chain(
    strikes: Iterable[int], forward: float = FORWARD, vol: float = VOL
) -> list[ChainPoint]:
    return [
        ChainPoint(
            Decimal(k), _px(OptionType.CALL, forward, k, vol), _px(OptionType.PUT, forward, k, vol)
        )
        for k in strikes
    ]


def chain_bars(
    points: Iterable[ChainPoint], day: date, expiry: date, symbol: str = "NIFTY"
) -> DayBars:
    """DayBars (settle = the point's price) for every priced option in `points`."""
    bars = {}
    for p in points:
        for option_type, px in ((OptionType.CALL, p.call), (OptionType.PUT, p.put)):
            if px is None:
                continue
            bar = make_bar(
                trade_date=day,
                symbol=symbol,
                expiry=expiry,
                strike=p.strike,
                option_type=option_type,
                settle=px,
                close=px,
            )
            bars[option_contract(bar)] = bar
    return bars

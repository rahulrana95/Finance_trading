"""Synthetic option chains priced with Black-76 at a flat volatility."""

from collections.abc import Iterable, Mapping
from datetime import date
from decimal import Decimal

from fintrade.backtest.data import DayBars, option_contract
from fintrade.core.bars import DailyContractBar, OptionType
from fintrade.core.pricing.black76 import price
from fintrade.core.pricing.chain import ChainPoint
from tests.support.bars import make_bar

FORWARD, YEARS, RATE, VOL = 25213.4, 8 / 365, 0.065, 0.13
EXPIRY_DAY_FRACTION = 0.25  # bars dated on expiry day still carry a little time value


def _px(option_type: OptionType, forward: float, strike: int, vol: float, years: float) -> Decimal:
    return Decimal(str(round(price(option_type, forward, float(strike), years, RATE, vol), 4)))


def flat_chain(
    strikes: Iterable[int], forward: float = FORWARD, vol: float = VOL, years: float = YEARS
) -> list[ChainPoint]:
    return [
        ChainPoint(
            Decimal(k),
            _px(OptionType.CALL, forward, k, vol, years),
            _px(OptionType.PUT, forward, k, vol, years),
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


def chain_history(
    forwards: Mapping[date, float],
    expiry: date,
    strikes: Iterable[int],
    vol: float = VOL,
    vols: Mapping[date, float] | None = None,
) -> list[DailyContractBar]:
    """Bars for one expiry's chain on each day, priced close-to-close at a flat vol
    (`vols` overrides the vol on the days it names)."""
    strikes = list(strikes)
    bars: list[DailyContractBar] = []
    for day, forward in forwards.items():
        years = max((expiry - day).days, EXPIRY_DAY_FRACTION) / 365
        day_vol = (vols or {}).get(day, vol)
        points = flat_chain(strikes, forward, day_vol, years)
        bars.extend(chain_bars(points, day, expiry).values())
    return bars

"""Black-76 pricing, implied volatility and Greeks on the forward price.

Thin typed wrapper over `vollib` (Jaeckel's "Let's Be Rational" IV solver). All vollib
quirks live here:
- invalid prices raise library-specific exceptions -> we return None
- a zero price returns IV 0 -> we return None (not a meaningful volatility)
- zero time to expiry divides by zero -> we reject it before calling

IV is only well-defined where an option has time value. Deep in-the-money prices are
nearly all intrinsic, so compute IV from the OUT-of-the-money side at each strike (calls
above the forward, puts below), as is standard practice.

Units: theta is per calendar day, vega per 1 volatility point (0.01), as vollib reports.
Greeks are floats (ENGINEERING.md section 5: floats only for Greeks / IV / scores).
"""

import math
from dataclasses import dataclass
from datetime import date, datetime, time

from py_lets_be_rational.exceptions import AboveMaximumException, BelowIntrinsicException
from vollib.black import black
from vollib.black.greeks import analytical
from vollib.black.implied_volatility import implied_volatility

from fintrade.core.bars import OptionType
from fintrade.core.errors import InvalidInputError
from fintrade.core.timezone import IST, ensure_ist

EXPIRY_CLOSE = time(15, 30)  # NSE closes at 15:30 IST; options settle at the close
SECONDS_PER_YEAR = 365 * 24 * 60 * 60
_FLAG = {OptionType.CALL: "c", OptionType.PUT: "p"}


@dataclass(frozen=True, slots=True)
class Greeks:
    price: float
    delta: float
    gamma: float
    theta_per_day: float
    vega_per_vol_point: float


def time_to_expiry_years(now: datetime, expiry: date) -> float:
    """Year fraction from `now` to the expiry-day close. Must be positive."""
    close = datetime.combine(expiry, EXPIRY_CLOSE, tzinfo=IST)
    seconds = (close - ensure_ist(now)).total_seconds()
    if seconds <= 0:
        raise InvalidInputError(f"{now.isoformat()} is at or after expiry close {close}")
    return seconds / SECONDS_PER_YEAR


def _check(forward: float, strike: float, years: float, rate: float) -> None:
    values = {"forward": forward, "strike": strike, "years": years}
    bad = [name for name, value in values.items() if not math.isfinite(value) or value <= 0]
    if bad or not math.isfinite(rate):
        raise InvalidInputError(f"invalid pricing inputs: {bad or ['rate']}")


def price(
    option_type: OptionType, forward: float, strike: float, years: float, rate: float, vol: float
) -> float:
    _check(forward, strike, years, rate)
    _check_vol(vol)
    return float(black(_FLAG[option_type], forward, strike, years, rate, vol))


def implied_vol(
    option_price: float,
    option_type: OptionType,
    forward: float,
    strike: float,
    years: float,
    rate: float,
) -> float | None:
    """Implied volatility, or None when no volatility can produce this price."""
    _check(forward, strike, years, rate)
    if not math.isfinite(option_price):
        raise InvalidInputError(f"option price must be finite: {option_price}")
    flag = _FLAG[option_type]
    try:
        vol = float(implied_volatility(option_price, forward, strike, rate, years, flag))
    except (BelowIntrinsicException, AboveMaximumException):
        return None
    return vol if vol > 0 else None


def greeks(
    option_type: OptionType, forward: float, strike: float, years: float, rate: float, vol: float
) -> Greeks:
    _check(forward, strike, years, rate)
    _check_vol(vol)
    args = (_FLAG[option_type], forward, strike, years, rate, vol)
    return Greeks(
        price=float(black(*args)),
        delta=float(analytical.delta(*args)),
        gamma=float(analytical.gamma(*args)),
        theta_per_day=float(analytical.theta(*args)),
        vega_per_vol_point=float(analytical.vega(*args)),
    )


def _check_vol(vol: float) -> None:
    if not math.isfinite(vol) or vol <= 0:
        raise InvalidInputError(f"volatility must be positive: {vol}")

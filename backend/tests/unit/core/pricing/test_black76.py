import math
from datetime import date, datetime

import pytest

from fintrade.core.bars import OptionType
from fintrade.core.errors import InvalidInputError
from fintrade.core.pricing.black76 import greeks, implied_vol, price, time_to_expiry_years
from fintrade.core.timezone import IST

CALL, PUT = OptionType.CALL, OptionType.PUT
F, K, T, R, VOL = 25200.0, 25800.0, 8 / 365, 0.065, 0.13


def _reference_black76(is_call: bool, f: float, k: float, t: float, r: float, v: float) -> float:
    """Independent textbook Black-76, written here to check the library."""

    def n(x: float) -> float:
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    d1 = (math.log(f / k) + 0.5 * v * v * t) / (v * math.sqrt(t))
    d2 = d1 - v * math.sqrt(t)
    df = math.exp(-r * t)
    if is_call:
        return df * (f * n(d1) - k * n(d2))
    return df * (k * n(-d2) - f * n(-d1))


def test_time_to_expiry_runs_to_the_expiry_day_close() -> None:
    years = time_to_expiry_years(datetime(2026, 10, 27, 10, 0, tzinfo=IST), date(2026, 11, 3))
    assert years == pytest.approx((7 + 5.5 / 24) / 365, rel=1e-12)


@pytest.mark.parametrize("hour_minute", [(15, 30), (15, 31)])
def test_time_to_expiry_rejects_at_or_after_close(hour_minute: tuple[int, int]) -> None:
    now = datetime(2026, 11, 3, *hour_minute, tzinfo=IST)
    with pytest.raises(InvalidInputError, match="at or after expiry close"):
        time_to_expiry_years(now, date(2026, 11, 3))


@pytest.mark.parametrize("option_type", [CALL, PUT])
def test_price_matches_independent_formula(option_type: OptionType) -> None:
    expected = _reference_black76(option_type is CALL, F, K, T, R, VOL)
    assert price(option_type, F, K, T, R, VOL) == pytest.approx(expected, rel=1e-10)


def test_golden_greeks_for_a_typical_short_call() -> None:
    # ~600 pts OTM call, 8 days, 13% vol: our typical short-strike zone.
    g = greeks(CALL, F, K, T, R, VOL)
    assert g.price == pytest.approx(26.2407, abs=1e-4)
    assert g.delta == pytest.approx(0.112406, abs=1e-6)
    assert g.theta_per_day == pytest.approx(-5.7818, abs=1e-4)
    assert g.vega_per_vol_point == pytest.approx(7.1218, abs=1e-4)
    assert g.gamma > 0


def test_delta_matches_numerical_derivative() -> None:
    bump = 0.01
    up = _reference_black76(True, F + bump, K, T, R, VOL)
    down = _reference_black76(True, F - bump, K, T, R, VOL)
    assert greeks(CALL, F, K, T, R, VOL).delta == pytest.approx((up - down) / (2 * bump), rel=1e-5)


def test_put_delta_is_negative() -> None:
    assert -1 < greeks(PUT, F, 24600.0, T, R, VOL).delta < 0


def test_implied_vol_round_trip() -> None:
    p = price(PUT, F, 24600.0, T, R, 0.15)
    assert implied_vol(p, PUT, F, 24600.0, T, R) == pytest.approx(0.15, rel=1e-9)


@pytest.mark.parametrize(
    ("option_price", "strike"),
    [(0.0, K), (1000.0, 24000.0), (30000.0, 24000.0), (-1.0, K)],
    ids=["zero price", "below intrinsic", "above maximum", "negative"],
)
def test_implied_vol_none_when_no_solution(option_price: float, strike: float) -> None:
    assert implied_vol(option_price, CALL, F, strike, T, R) is None


@pytest.mark.parametrize(
    ("forward", "strike", "years", "rate"),
    [(-1.0, K, T, R), (F, 0.0, T, R), (F, K, 0.0, R), (F, K, T, math.nan), (math.inf, K, T, R)],
)
def test_invalid_inputs_rejected(forward: float, strike: float, years: float, rate: float) -> None:
    with pytest.raises(InvalidInputError, match="invalid pricing inputs"):
        greeks(CALL, forward, strike, years, rate, VOL)
    with pytest.raises(InvalidInputError, match="invalid pricing inputs"):
        implied_vol(10.0, CALL, forward, strike, years, rate)


@pytest.mark.parametrize("vol", [0.0, -0.1, math.nan])
def test_invalid_volatility_rejected(vol: float) -> None:
    with pytest.raises(InvalidInputError, match="volatility must be positive"):
        price(CALL, F, K, T, R, vol)
    with pytest.raises(InvalidInputError, match="volatility must be positive"):
        greeks(CALL, F, K, T, R, vol)


def test_non_finite_option_price_rejected() -> None:
    with pytest.raises(InvalidInputError, match="option price must be finite"):
        implied_vol(math.nan, CALL, F, K, T, R)

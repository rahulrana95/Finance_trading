"""Properties that must hold for any sensible inputs."""

import math

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from fintrade.core.bars import OptionType
from fintrade.core.pricing.black76 import greeks, implied_vol, price

forwards = st.floats(10_000, 40_000)
moneyness = st.floats(0.85, 1.15)
years = st.floats(1 / 365, 60 / 365)
rates = st.floats(0.0, 0.10)
vols = st.floats(0.05, 0.80)


@given(f=forwards, m=moneyness, t=years, r=rates, v=vols)
def test_put_call_parity(f: float, m: float, t: float, r: float, v: float) -> None:
    k = f * m
    call = price(OptionType.CALL, f, k, t, r, v)
    put = price(OptionType.PUT, f, k, t, r, v)
    assert call - put == pytest.approx(math.exp(-r * t) * (f - k), abs=1e-6 * f)


@given(f=forwards, m=moneyness, t=years, r=rates, v=vols)
def test_call_minus_put_delta_is_discount_factor(
    f: float, m: float, t: float, r: float, v: float
) -> None:
    k = f * m
    call = greeks(OptionType.CALL, f, k, t, r, v)
    put = greeks(OptionType.PUT, f, k, t, r, v)
    assert call.delta - put.delta == pytest.approx(math.exp(-r * t), abs=1e-9)
    assert 0 <= call.delta <= 1
    assert call.gamma == pytest.approx(put.gamma, rel=1e-9)
    assert call.vega_per_vol_point >= 0


@given(f=forwards, m=moneyness, t=years, r=rates, v=vols, is_call=st.booleans())
def test_implied_vol_recovers_the_input_vol(
    f: float, m: float, t: float, r: float, v: float, is_call: bool
) -> None:
    option_type = OptionType.CALL if is_call else OptionType.PUT
    k = f * m
    p = price(option_type, f, k, t, r, v)
    intrinsic = math.exp(-r * t) * max(f - k if is_call else k - f, 0.0)
    # IV lives in the time value. With almost none (far OTM, or deep ITM where price is
    # nearly all intrinsic) it can't be inverted precisely; use the OTM side instead.
    assume(p - intrinsic > 0.01)
    recovered = implied_vol(p, option_type, f, k, t, r)
    assert recovered == pytest.approx(v, rel=1e-6)

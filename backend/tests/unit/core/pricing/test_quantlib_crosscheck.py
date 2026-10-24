"""Cross-check our Black-76 wrapper (vollib) against QuantLib, an independent library."""

import math

import pytest
import QuantLib as ql  # noqa: N813 - standard alias

from fintrade.core.bars import OptionType
from fintrade.core.pricing.black76 import greeks, implied_vol

R = 0.065
DAYS_PER_YEAR = 365
VOL_POINT = 0.01
_QL_TYPE = {OptionType.CALL: ql.Option.Call, OptionType.PUT: ql.Option.Put}


def _quantlib(
    option_type: OptionType, f: float, k: float, t: float, v: float
) -> ql.BlackCalculator:
    payoff = ql.PlainVanillaPayoff(_QL_TYPE[option_type], k)
    return ql.BlackCalculator(payoff, f, v * math.sqrt(t), math.exp(-R * t))


GRID = [
    (option_type, 22600.0 * m, days / DAYS_PER_YEAR, vol)
    for option_type in (OptionType.CALL, OptionType.PUT)
    for m in (0.92, 0.97, 1.0, 1.03, 1.08)
    for days in (1, 6, 8, 13, 30)
    for vol in (0.10, 0.16, 0.35)
]


@pytest.mark.parametrize(("option_type", "strike", "years", "vol"), GRID)
def test_price_and_greeks_match_quantlib(
    option_type: OptionType, strike: float, years: float, vol: float
) -> None:
    forward = 22600.0
    ours = greeks(option_type, forward, strike, years, R, vol)
    ref = _quantlib(option_type, forward, strike, years, vol)
    assert ours.price == pytest.approx(ref.value(), rel=1e-8, abs=1e-9)
    assert ours.delta == pytest.approx(ref.deltaForward(), rel=1e-8, abs=1e-12)
    assert ours.gamma == pytest.approx(ref.gammaForward(), rel=1e-7, abs=1e-12)
    assert ours.vega_per_vol_point == pytest.approx(ref.vega(years) * VOL_POINT, rel=1e-8, abs=1e-9)
    assert ours.theta_per_day == pytest.approx(
        ref.theta(forward, years) / DAYS_PER_YEAR, rel=1e-7, abs=1e-9
    )


QL_IV_ACCURACY = 1e-12  # QuantLib's default (1e-6) is looser than our solver
FORWARD = 22600.0


def _is_out_of_the_money(option_type: OptionType, strike: float) -> bool:
    """IV is taken from the OTM side at each strike (see black76 docstring)."""
    return strike >= FORWARD if option_type is OptionType.CALL else strike <= FORWARD


NSE_TICK = 0.05  # smallest price step; anything cheaper can't trade and has no IV information


def _tradeable(option_type: OptionType, strike: float, years: float, vol: float) -> bool:
    value: float = _quantlib(option_type, FORWARD, strike, years, vol).value()
    return value >= NSE_TICK


IV_GRID = [c for c in GRID if _is_out_of_the_money(c[0], c[1]) and _tradeable(*c)]


def test_iv_grid_covers_most_otm_cases() -> None:
    otm = [c for c in GRID if _is_out_of_the_money(c[0], c[1])]
    assert len(otm) == 90  # 2 types x 3 OTM-or-ATM moneyness x 5 times x 3 vols
    assert len(IV_GRID) == 71  # 19 sub-tick far-OTM, short-dated, low-vol cases dropped


@pytest.mark.parametrize(("option_type", "strike", "years", "vol"), IV_GRID)
def test_implied_vol_matches_quantlib(
    option_type: OptionType, strike: float, years: float, vol: float
) -> None:
    option_price = _quantlib(option_type, FORWARD, strike, years, vol).value()
    ql_std_dev = ql.blackFormulaImpliedStdDev(
        _QL_TYPE[option_type], strike, FORWARD, option_price, math.exp(-R * years),
        0.0, vol * math.sqrt(years), QL_IV_ACCURACY,
    )  # fmt: skip
    ours = implied_vol(option_price, option_type, FORWARD, strike, years, R)
    assert ours == pytest.approx(ql_std_dev / math.sqrt(years), rel=1e-8)
    assert ours == pytest.approx(vol, rel=1e-8)


def test_one_hour_to_expiry_still_matches() -> None:
    years = 1 / (DAYS_PER_YEAR * 24)
    ours = greeks(OptionType.CALL, 22600.0, 22650.0, years, R, 0.15)
    ref = _quantlib(OptionType.CALL, 22600.0, 22650.0, years, 0.15)
    assert ours.price == pytest.approx(ref.value(), rel=1e-8)
    assert ours.delta == pytest.approx(ref.deltaForward(), rel=1e-8)

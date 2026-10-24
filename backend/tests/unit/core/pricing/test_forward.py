import math

import pytest

from fintrade.core.bars import OptionType
from fintrade.core.errors import DataError, InvalidInputError
from fintrade.core.pricing.black76 import price
from fintrade.core.pricing.forward import StrikeQuote, forward_from_chain

TRUE_F, T, R, VOL = 25213.4, 8 / 365, 0.065, 0.13


def _chain(strikes: range) -> list[StrikeQuote]:
    return [
        StrikeQuote(
            strike=float(k),
            call=price(OptionType.CALL, TRUE_F, float(k), T, R, VOL),
            put=price(OptionType.PUT, TRUE_F, float(k), T, R, VOL),
        )
        for k in strikes
    ]


def test_recovers_forward_from_consistent_chain() -> None:
    quotes = _chain(range(24000, 26500, 50))
    assert forward_from_chain(quotes, T, R) == pytest.approx(TRUE_F, abs=1e-6)


def test_one_bad_quote_does_not_move_the_forward() -> None:
    quotes = _chain(range(25000, 25450, 50))
    bad = quotes[4]  # strike 25200, nearest the money
    quotes[4] = StrikeQuote(bad.strike, bad.call + 40, bad.put)
    assert forward_from_chain(quotes, T, R) == pytest.approx(TRUE_F, abs=1e-6)


def test_uses_strikes_nearest_the_money() -> None:
    near = _chain(range(25100, 25350, 50))
    far_wrong = [StrikeQuote(30000.0, 1.0, 4000.0)] * 10  # nonsense far from the money
    assert forward_from_chain([*near, *far_wrong], T, R) == pytest.approx(TRUE_F, abs=1e-6)


def test_quotes_missing_a_side_are_ignored() -> None:
    quotes = [*_chain(range(25150, 25300, 50)), StrikeQuote(25300.0, 0.0, 120.0)]
    assert forward_from_chain(quotes, T, R) == pytest.approx(TRUE_F, abs=1e-6)


def test_no_usable_quotes_is_a_data_error() -> None:
    with pytest.raises(DataError, match="no strike with both"):
        forward_from_chain([StrikeQuote(25200.0, 0.0, 10.0)], T, R)


@pytest.mark.parametrize(("years", "rate"), [(0.0, R), (-T, R), (math.nan, R), (T, math.inf)])
def test_invalid_time_or_rate_rejected(years: float, rate: float) -> None:
    with pytest.raises(InvalidInputError):
        forward_from_chain(_chain(range(25200, 25250, 50)), years, rate)

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from fintrade.core.bars import OptionType
from fintrade.core.errors import InvalidInputError
from fintrade.core.instruments import (
    CreditSpread,
    Leg,
    OptionContract,
    Side,
    Structure,
    credit_spread,
)
from tests.support.instruments import EXPIRY, bear_call, bull_put


def test_bull_put_properties() -> None:
    spread = bull_put()
    assert spread.structure is Structure.BULL_PUT
    assert spread.width == Decimal(200)
    assert (spread.expiry, spread.lots) == (EXPIRY, 2)
    assert spread.legs == (spread.short, spread.long)


def test_bear_call_properties() -> None:
    spread = bear_call(short=25800, long=25900)
    assert spread.structure is Structure.BEAR_CALL
    assert spread.option_type is OptionType.CALL
    assert spread.width == Decimal(100)


@pytest.mark.parametrize(
    "build",
    [lambda: bull_put(short=24400, long=24600), lambda: bear_call(short=26000, long=25800)],
)
def test_hedge_on_wrong_side_rejected(build: object) -> None:
    with pytest.raises(InvalidInputError, match="further out of the money"):
        build()  # type: ignore[operator]


def test_hedge_at_same_strike_rejected() -> None:
    with pytest.raises(InvalidInputError, match="further out of the money"):
        bull_put(short=24600, long=24600)


def test_naked_or_reversed_sides_rejected() -> None:
    spread = bull_put()
    with pytest.raises(InvalidInputError, match="SELL short leg and a BUY long leg"):
        CreditSpread(short=replace(spread.short, side=Side.BUY), long=spread.long)
    with pytest.raises(InvalidInputError, match="SELL short leg and a BUY long leg"):
        CreditSpread(short=spread.short, long=replace(spread.long, side=Side.SELL))


def test_hedge_on_other_expiry_rejected() -> None:
    spread = bull_put()
    other = replace(spread.long.contract, expiry=date(2026, 11, 10))
    with pytest.raises(InvalidInputError, match="same expiry"):
        CreditSpread(short=spread.short, long=replace(spread.long, contract=other))


def test_mixed_call_and_put_rejected() -> None:
    spread = bull_put()
    call = replace(spread.long.contract, option_type=OptionType.CALL)
    with pytest.raises(InvalidInputError, match="both be calls or both be puts"):
        CreditSpread(short=spread.short, long=replace(spread.long, contract=call))


def test_different_underlying_rejected() -> None:
    spread = bull_put()
    other = replace(spread.long.contract, symbol="BANKNIFTY")
    with pytest.raises(InvalidInputError, match="same underlying"):
        CreditSpread(short=spread.short, long=replace(spread.long, contract=other))


def test_partial_hedge_rejected() -> None:
    spread = bull_put(lots=2)
    with pytest.raises(InvalidInputError, match="lot for lot"):
        CreditSpread(short=spread.short, long=replace(spread.long, lots=1))


@pytest.mark.parametrize("lots", [0, -1, True, 1.5])
def test_bad_lots_rejected(lots: object) -> None:
    contract = bull_put().short.contract
    with pytest.raises(InvalidInputError, match="lots must be a positive int"):
        Leg(contract, Side.SELL, lots)  # type: ignore[arg-type]


@pytest.mark.parametrize("strike", ["0", "-100", "NaN", "Infinity"])
def test_bad_strike_rejected(strike: str) -> None:
    with pytest.raises(InvalidInputError, match="strike must be positive"):
        OptionContract("NIFTY", EXPIRY, Decimal(strike), OptionType.PUT)


def test_empty_symbol_rejected() -> None:
    with pytest.raises(InvalidInputError, match="symbol is empty"):
        OptionContract("", EXPIRY, Decimal(24000), OptionType.PUT)


strikes = st.integers(min_value=1, max_value=1000).map(lambda n: Decimal(n * 50))


@given(short=strikes, long=strikes, is_put=st.booleans(), lots=st.integers(1, 50))
def test_any_constructed_spread_has_positive_width(
    short: Decimal, long: Decimal, is_put: bool, lots: int
) -> None:
    option_type = OptionType.PUT if is_put else OptionType.CALL
    correct_side = long < short if is_put else long > short
    build = {
        "symbol": "NIFTY", "expiry": EXPIRY, "option_type": option_type,
        "short_strike": short, "long_strike": long, "lots": lots,
    }  # fmt: skip
    if correct_side:
        assert credit_spread(**build).width == abs(short - long)  # type: ignore[arg-type]
    else:
        with pytest.raises(InvalidInputError):
            credit_spread(**build)  # type: ignore[arg-type]

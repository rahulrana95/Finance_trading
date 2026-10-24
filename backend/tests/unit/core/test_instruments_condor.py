from dataclasses import replace

import pytest

from fintrade.core.errors import InvalidInputError
from fintrade.core.instruments import IronCondor, Side, Structure
from tests.support.instruments import EXPIRY, bear_call, bull_put, iron_condor


def test_iron_condor_properties() -> None:
    condor = iron_condor(lots=3)
    assert condor.structure is Structure.IRON_CONDOR
    assert (condor.expiry, condor.lots) == (EXPIRY, 3)
    assert [leg.side for leg in condor.legs] == [Side.SELL, Side.BUY, Side.SELL, Side.BUY]


def test_sides_swapped_rejected() -> None:
    with pytest.raises(InvalidInputError, match="put side must be a bull put"):
        IronCondor(put_spread=bear_call(), call_spread=bear_call(short=26000, long=26200))
    with pytest.raises(InvalidInputError, match="call side must be a bear call"):
        IronCondor(put_spread=bull_put(), call_spread=bull_put(short=24400, long=24200))


def test_different_expiries_rejected() -> None:
    call = bear_call()
    later = replace(call.short.contract, expiry=EXPIRY.replace(day=10))
    later_long = replace(call.long.contract, expiry=EXPIRY.replace(day=10))
    shifted = type(call)(
        short=replace(call.short, contract=later), long=replace(call.long, contract=later_long)
    )
    with pytest.raises(InvalidInputError, match="share one expiry"):
        IronCondor(put_spread=bull_put(), call_spread=shifted)


def test_different_lots_rejected() -> None:
    with pytest.raises(InvalidInputError, match="same lots"):
        IronCondor(put_spread=bull_put(lots=1), call_spread=bear_call(lots=2))


@pytest.mark.parametrize("put_short", [25800, 25900])
def test_overlapping_short_strikes_rejected(put_short: int) -> None:
    with pytest.raises(InvalidInputError, match="short put strike must be below"):
        IronCondor(
            put_spread=bull_put(short=put_short, long=put_short - 200),
            call_spread=bear_call(short=25800, long=26000),
        )

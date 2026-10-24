import math
from dataclasses import replace
from decimal import Decimal

import pytest

from fintrade.core.bars import OptionType
from fintrade.core.errors import DataError
from fintrade.core.pricing.chain import ChainPoint, chain_greeks
from tests.support.chain import FORWARD, RATE, VOL, YEARS, flat_chain

TICK = Decimal("0.05")
STRIKES = range(23500, 27050, 50)


def test_recovers_forward_and_flat_vol() -> None:
    result = chain_greeks(flat_chain(STRIKES), YEARS, RATE, TICK)
    assert result.forward == pytest.approx(FORWARD, abs=0.01)
    ivs = [g.iv for g in result.by_strike.values()]
    assert len(ivs) > 40
    assert ivs == pytest.approx([VOL] * len(ivs), abs=5e-4)


def test_call_and_put_deltas_follow_parity_and_sign() -> None:
    result = chain_greeks(flat_chain(STRIKES), YEARS, RATE, TICK)
    discount = math.exp(-RATE * YEARS)
    for g in result.by_strike.values():
        assert g.call.delta - g.put.delta == pytest.approx(discount, abs=1e-9)
        assert g.of(OptionType.CALL) is g.call
        assert g.of(OptionType.PUT) is g.put
        assert 0 < g.call.delta < 1
        assert -1 < g.put.delta < 0


def test_otm_side_sets_the_iv() -> None:
    chain = flat_chain([25000, 25200, 25250, 25500])
    # corrupt the ITM side of 25500 (the put): IV must still come from the call
    chain[3] = replace(chain[3], put=chain[3].put + Decimal(30))  # type: ignore[operator]
    result = chain_greeks(chain, YEARS, RATE, TICK)
    assert result.by_strike[Decimal(25500)].iv == pytest.approx(VOL, abs=5e-4)


def test_sub_tick_and_missing_otm_prices_left_out() -> None:
    chain = flat_chain([24000, 25000, 25200, 25250, 25400, 27500])
    far_call = chain[-1]
    assert far_call.call is not None
    assert far_call.call < TICK  # far OTM call is sub-tick at 13% vol, 8 days
    chain[0] = ChainPoint(Decimal(24000), chain[0].call, None)  # OTM put missing
    result = chain_greeks(chain, YEARS, RATE, TICK)
    assert set(result.by_strike) == {Decimal(k) for k in (25000, 25200, 25250, 25400)}


def test_price_with_no_iv_left_out() -> None:
    chain = flat_chain([25000, 25200, 25250, 25400])
    chain.append(ChainPoint(Decimal(26000), Decimal(50_000), None))  # above any call value
    result = chain_greeks(chain, YEARS, RATE, TICK)
    assert Decimal(26000) not in result.by_strike


def test_no_complete_pair_fails_loudly() -> None:
    with pytest.raises(DataError):
        chain_greeks([ChainPoint(Decimal(25000), Decimal(10), None)], YEARS, RATE, TICK)

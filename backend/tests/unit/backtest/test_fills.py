"""Fill simulator: daily bars carry no bid/ask, so fills are modelled conservatively."""

from dataclasses import replace
from decimal import Decimal
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from fintrade.backtest.fills import (
    BarFillModel,
    FillConfig,
    PriceBasis,
    ProportionalSpread,
    fill_price,
)
from fintrade.core.errors import DataError, InvalidInputError
from fintrade.core.instruments import Side
from tests.support.bars import make_bar

TICK = Decimal("0.05")
# 2% half-spread, at least 2 ticks; 1 tick slippage
SPREAD = ProportionalSpread(half_spread_pct=Decimal(2), min_half_spread_ticks=2)
CONFIG = FillConfig(basis=PriceBasis.SETTLE, tick_size=TICK, slippage_ticks=1)


def _model(config: FillConfig = CONFIG) -> BarFillModel:
    return BarFillModel(config, SPREAD)


def test_buy_pays_and_sell_receives_spread_plus_slippage() -> None:
    bar = make_bar(settle=Decimal(40), close=Decimal(40))
    # half spread 2% of 40 = 0.80; slippage 0.05
    assert _model().fill(bar, Side.BUY) == Decimal("40.85")
    assert _model().fill(bar, Side.SELL) == Decimal("39.15")


def test_minimum_spread_applies_to_cheap_options() -> None:
    bar = make_bar(settle=Decimal("1.00"), close=Decimal("1.00"))
    # 2% of 1.00 = 0.02 < 2 ticks (0.10); slippage 0.05
    assert _model().fill(bar, Side.BUY) == Decimal("1.15")
    assert _model().fill(bar, Side.SELL) == Decimal("0.85")


def test_rounds_against_us_to_the_tick() -> None:
    bar = make_bar(settle=Decimal("12.30"), close=Decimal("12.30"))
    # half spread 0.246 -> buy 12.596 rounds up to 12.60, sell 12.004 rounds down to 12.00
    assert _model().fill(bar, Side.BUY) == Decimal("12.60")
    assert _model().fill(bar, Side.SELL) == Decimal("12.00")


def test_sell_of_worthless_option_floors_at_zero() -> None:
    bar = make_bar(settle=Decimal("0.05"), close=Decimal("0.05"))
    assert _model().fill(bar, Side.SELL) == 0
    assert _model().fill(bar, Side.BUY) == Decimal("0.20")


@pytest.mark.parametrize(
    ("basis", "buy", "sell"),
    [
        (PriceBasis.SETTLE, "41.85", "40.15"),  # settle 41
        (PriceBasis.CLOSE, "40.85", "39.15"),  # close 40
        (PriceBasis.WORST, "41.85", "39.15"),  # buy from the higher, sell from the lower
    ],
)
def test_price_basis(basis: PriceBasis, buy: str, sell: str) -> None:
    bar = make_bar(settle=Decimal(41), close=Decimal(40))
    spread = ProportionalSpread(half_spread_pct=Decimal(0), min_half_spread_ticks=16)  # 0.80
    model = BarFillModel(replace(CONFIG, basis=basis), spread)
    assert (model.fill(bar, Side.BUY), model.fill(bar, Side.SELL)) == (Decimal(buy), Decimal(sell))


def test_default_config_is_conservative() -> None:
    config = FillConfig()
    assert config.basis is PriceBasis.WORST
    assert config.slippage_ticks >= 1
    assert config.tick_size == TICK


@pytest.mark.parametrize("bad", [Decimal(0), Decimal("-1"), Decimal("NaN")])
def test_non_positive_reference_price_fails_loudly(bad: Decimal) -> None:
    with pytest.raises(DataError, match="reference price"):
        fill_price(bad, Side.BUY, half_spread=Decimal("0.1"), config=CONFIG)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"tick_size": Decimal(0)},
        {"tick_size": Decimal("-0.05")},
        {"tick_size": Decimal("NaN")},
        {"slippage_ticks": -1},
    ],
)
def test_invalid_fill_config_rejected(kwargs: dict[str, Any]) -> None:
    with pytest.raises(InvalidInputError):
        replace(CONFIG, **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"half_spread_pct": Decimal(-1)},
        {"half_spread_pct": Decimal("NaN")},
        {"half_spread_pct": Decimal(100)},
        {"min_half_spread_ticks": -1},
    ],
)
def test_invalid_spread_model_rejected(kwargs: dict[str, Any]) -> None:
    with pytest.raises(InvalidInputError):
        replace(SPREAD, **kwargs)


def test_negative_half_spread_rejected() -> None:
    with pytest.raises(InvalidInputError, match="half spread"):
        fill_price(Decimal(10), Side.BUY, half_spread=Decimal("-0.1"), config=CONFIG)


@given(
    ticks=st.integers(min_value=1, max_value=100_000),
    pct=st.decimals(min_value=0, max_value=20, places=2),
    min_ticks=st.integers(min_value=0, max_value=10),
    slip=st.integers(min_value=0, max_value=5),
)
def test_fills_always_worse_than_reference_and_on_tick(
    ticks: int, pct: Decimal, min_ticks: int, slip: int
) -> None:
    ref = TICK * ticks
    bar = make_bar(settle=ref, close=ref)
    model = BarFillModel(replace(CONFIG, slippage_ticks=slip), ProportionalSpread(pct, min_ticks))
    buy, sell = model.fill(bar, Side.BUY), model.fill(bar, Side.SELL)
    assert buy >= ref >= sell >= 0
    assert buy % TICK == 0
    assert sell % TICK == 0
    if sell > 0:
        assert buy - sell >= 2 * TICK * (min_ticks + slip)


@pytest.mark.parametrize("basis", [PriceBasis.SETTLE, PriceBasis.WORST])
def test_unreported_settle_uses_close(basis: PriceBasis) -> None:
    bar = make_bar(settle=Decimal(0), close=Decimal(40))
    model = BarFillModel(replace(CONFIG, basis=basis), SPREAD)
    assert model.fill(bar, Side.SELL) == Decimal("39.15")

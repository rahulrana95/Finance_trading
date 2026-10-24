from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from fintrade.core.errors import DataError, InvalidInputError
from fintrade.core.instruments import CreditSpread, Position
from fintrade.core.pnl import (
    OpenPosition,
    Prices,
    credit_points,
    mark_to_market,
    portfolio_mark_to_market,
    portfolio_max_loss,
    risk,
)
from tests.support.instruments import bear_call, bull_put, iron_condor

LOT = 65


def _prices(position: Position, *values: str) -> Prices:
    return {leg.contract: Decimal(v) for leg, v in zip(position.legs, values, strict=True)}


def test_golden_bull_put_risk() -> None:
    spread = bull_put()  # 24600 / 24400, 2 lots
    r = risk(spread, _prices(spread, "42.50", "12.00"), LOT)
    assert r.credit_points == Decimal("30.50")
    assert r.max_profit == Decimal("3965.00")  # 30.50 x 130
    assert r.max_loss == Decimal("22035.00")  # (200 - 30.50) x 130


def test_golden_iron_condor_risk_counts_one_side_only() -> None:
    condor = iron_condor()
    r = risk(condor, _prices(condor, "42.50", "12.00", "38.00", "10.00"), LOT)
    assert r.credit_points == Decimal("58.50")
    assert r.max_profit == Decimal("7605.00")
    assert r.max_loss == Decimal("18395.00")  # (200 - 58.50) x 130, not both sides


def test_iron_condor_uses_the_wider_side() -> None:
    condor = type(iron_condor())(put_spread=bull_put(), call_spread=bear_call(25800, 26100))
    r = risk(condor, _prices(condor, "40", "10", "40", "10"), LOT)
    assert r.max_loss == (Decimal(300) - Decimal(60)) * 130


def test_golden_mark_to_market() -> None:
    spread = bull_put()
    entry = _prices(spread, "42.50", "12.00")
    now = _prices(spread, "60.00", "18.00")  # market fell: short +17.50, hedge +6.00
    assert mark_to_market(spread, entry, now, LOT) == Decimal("-1495.00")


def test_mark_to_market_at_entry_prices_is_zero() -> None:
    condor = iron_condor()
    prices = _prices(condor, "42.50", "12.00", "38.00", "10.00")
    assert mark_to_market(condor, prices, prices, LOT) == 0


def test_portfolio_totals() -> None:
    spread, condor = bull_put(), iron_condor(lots=1)
    book = [
        OpenPosition(spread, _prices(spread, "42.50", "12.00"), LOT),
        OpenPosition(condor, _prices(condor, "42.50", "12.00", "38.00", "10.00"), LOT),
    ]
    assert portfolio_max_loss(book) == Decimal("22035.00") + Decimal("141.50") * 65
    now = {**book[0].entry, **book[1].entry}
    assert portfolio_mark_to_market(book, now) == 0
    assert portfolio_max_loss([]) == 0


def test_missing_price_fails_closed() -> None:
    spread = bull_put()
    with pytest.raises(DataError, match="no price for"):
        credit_points(spread, {spread.short.contract: Decimal(40)})


@pytest.mark.parametrize("bad", ["-1", "NaN", "Infinity"])
def test_invalid_price_rejected(bad: str) -> None:
    spread = bull_put()
    with pytest.raises(DataError, match="invalid price"):
        credit_points(spread, _prices(spread, bad, "10"))


def test_credit_wider_than_spread_is_impossible() -> None:
    spread = bull_put()
    with pytest.raises(DataError, match="exceeds width"):
        risk(spread, _prices(spread, "250", "10"), LOT)


def test_debit_entry_is_reported_honestly() -> None:
    spread = bull_put()
    r = risk(spread, _prices(spread, "10", "12"), LOT)  # paid 2 to enter
    assert (r.credit_points, r.max_profit, r.max_loss) == (
        Decimal(-2),
        Decimal(-260),
        Decimal(26260),
    )


@pytest.mark.parametrize("lot", [0, -65, True, 65.0])
def test_bad_lot_size_rejected(lot: object) -> None:
    spread = bull_put()
    with pytest.raises(InvalidInputError, match="lot size must be a positive int"):
        risk(spread, _prices(spread, "40", "10"), lot)  # type: ignore[arg-type]


prices = st.decimals(min_value=0, max_value=200, places=2)


@given(short=prices, long=prices, lots=st.integers(1, 20))
def test_max_profit_plus_max_loss_is_width_times_units(
    short: Decimal, long: Decimal, lots: int
) -> None:
    spread = bull_put(lots=lots)
    entry = _prices(spread, str(short), str(long))
    r = risk(spread, entry, LOT)
    assert r.max_profit + r.max_loss == spread.width * lots * LOT


@given(entry_short=prices, entry_long=prices, now_long=prices, now_gap=prices)
def test_open_loss_never_exceeds_max_loss(
    entry_short: Decimal, entry_long: Decimal, now_long: Decimal, now_gap: Decimal
) -> None:
    spread: CreditSpread = bull_put()
    entry = _prices(spread, str(entry_short), str(entry_long))
    # No-arbitrage: the short put is worth at least the hedge, and at most `width` more.
    now = _prices(spread, str(now_long + min(now_gap, spread.width)), str(now_long))
    r = risk(spread, entry, LOT)
    assert mark_to_market(spread, entry, now, LOT) >= -r.max_loss

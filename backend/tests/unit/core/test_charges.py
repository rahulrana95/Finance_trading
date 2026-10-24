from datetime import date
from decimal import Decimal

import pytest

from fintrade.core.charges import (
    CHARGE_SCHEDULE,
    GROWW_FNO,
    BrokeragePlan,
    order_charges,
    rates_on,
)
from fintrade.core.errors import InvalidInputError
from fintrade.core.instruments import Side

NOW = date(2026, 10, 26)


def test_golden_sell_order_2026() -> None:
    # 2 lots x 65 at Rs 42.50: turnover 5525.
    c = order_charges(Side.SELL, Decimal("42.50"), 130, NOW)
    assert c.brokerage == Decimal(20)
    assert c.stt == Decimal("8.2875")  # 0.15% of 5525
    assert c.exchange == Decimal("1.9630325")  # 0.03553%
    assert c.sebi == c.ipft == Decimal("0.005525")  # 0.0001%
    assert c.stamp == Decimal(0)  # stamp duty is buy side only
    assert c.gst == Decimal("3.95533485")  # 18% of 21.9740825
    assert c.total == Decimal("34.22")


def test_golden_buy_order_2026() -> None:
    # Hedge leg: 130 units at Rs 12.00, turnover 1560.
    c = order_charges(Side.BUY, Decimal(12), 130, NOW)
    assert c.stt == Decimal(0)  # no STT on buying options
    assert c.stamp == Decimal("0.0468")  # 0.003%
    assert c.total == Decimal("24.30")


def test_golden_sell_order_2022_uses_old_rates() -> None:
    # 2 lots x 75 at Rs 40, turnover 6000: STT 0.05%, exchange 0.053%.
    c = order_charges(Side.SELL, Decimal(40), 150, date(2022, 6, 1))
    assert (c.stt, c.exchange) == (Decimal("3.0000"), Decimal("3.18000"))
    assert c.total == Decimal("30.37")


@pytest.mark.parametrize(
    ("day", "stt"),
    [
        (date(2019, 2, 11), "0.05"),
        (date(2023, 3, 31), "0.05"),
        (date(2023, 4, 1), "0.0625"),
        (date(2024, 9, 30), "0.0625"),
        (date(2024, 10, 1), "0.1"),
        (date(2026, 3, 31), "0.1"),
        (date(2026, 4, 1), "0.15"),
    ],
)
def test_stt_changes_on_the_right_days(day: date, stt: str) -> None:
    assert rates_on(day).stt_sell_pct == Decimal(stt)


def test_schedule_is_sorted_and_never_cheaper_on_exchange_before_2024() -> None:
    starts = [r.effective_from for r in CHARGE_SCHEDULE]
    assert starts == sorted(starts)
    assert rates_on(date(2024, 9, 30)).exchange_pct >= rates_on(date(2024, 10, 1)).exchange_pct


def test_date_before_schedule_rejected() -> None:
    with pytest.raises(InvalidInputError, match="no charge schedule before 2019-01-01"):
        rates_on(date(2018, 12, 31))


def test_zero_price_still_pays_brokerage() -> None:
    c = order_charges(Side.BUY, Decimal(0), 65, NOW)
    assert c.total == Decimal("23.60")  # 20 brokerage + 18% GST


def test_custom_brokerage_plan() -> None:
    cheap = order_charges(Side.BUY, Decimal(10), 65, NOW, BrokeragePlan(Decimal(0)))
    groww = order_charges(Side.BUY, Decimal(10), 65, NOW, GROWW_FNO)
    assert groww.total - cheap.total == Decimal("23.60")


@pytest.mark.parametrize("price", [Decimal(-1), Decimal("NaN"), Decimal("Infinity")])
def test_bad_price_rejected(price: Decimal) -> None:
    with pytest.raises(InvalidInputError, match="price must be"):
        order_charges(Side.SELL, price, 65, NOW)


@pytest.mark.parametrize("quantity", [0, -65, True, 65.0])
def test_bad_quantity_rejected(quantity: object) -> None:
    with pytest.raises(InvalidInputError, match="quantity must be a positive int"):
        order_charges(Side.SELL, Decimal(10), quantity, NOW)  # type: ignore[arg-type]

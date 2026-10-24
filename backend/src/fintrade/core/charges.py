"""Transaction charges for NSE index options, by trade date (AGENTS.md section 5).

Statutory rates change over time, so the backtest must charge what applied on each day.
Where history could not be fully verified, the HIGHER known rate is used: a backtest
must never look cheaper than reality.

Sources (checked 2026-10-24): Zerodha and Groww charge pages; STT history from the
Finance Acts 2023, 2024 and 2026 (section 159, NSE circular NSE/FATAX/73524).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from fintrade.core.errors import InvalidInputError
from fintrade.core.instruments import Side
from fintrade.core.money import Rupees, round_rupees

_PCT = Decimal(100)


@dataclass(frozen=True, slots=True)
class ChargeRates:
    """All rates are percentages of premium turnover (price x quantity)."""

    effective_from: date
    stt_sell_pct: Decimal
    exchange_pct: Decimal
    sebi_pct: Decimal
    stamp_buy_pct: Decimal
    ipft_pct: Decimal
    gst_pct: Decimal  # on brokerage + exchange + SEBI + IPFT


def _rates(effective_from: date, stt: str, exchange: str) -> ChargeRates:
    return ChargeRates(
        effective_from=effective_from,
        stt_sell_pct=Decimal(stt),
        exchange_pct=Decimal(exchange),
        sebi_pct=Decimal("0.0001"),  # Rs 10 per crore
        stamp_buy_pct=Decimal("0.003"),
        ipft_pct=Decimal("0.0001"),  # NSE IPFT; tiny, conservative value
        gst_pct=Decimal(18),
    )


# Exchange charge before 2024-10-01 not fully verified: 0.053% (highest known) is used.
CHARGE_SCHEDULE: tuple[ChargeRates, ...] = (
    _rates(date(2019, 1, 1), stt="0.05", exchange="0.053"),
    _rates(date(2023, 4, 1), stt="0.0625", exchange="0.053"),
    _rates(date(2024, 10, 1), stt="0.1", exchange="0.03553"),
    _rates(date(2026, 4, 1), stt="0.15", exchange="0.03553"),
)


@dataclass(frozen=True, slots=True)
class BrokeragePlan:
    per_order_rupees: Rupees


GROWW_FNO = BrokeragePlan(per_order_rupees=Decimal(20))


@dataclass(frozen=True, slots=True)
class OrderCharges:
    brokerage: Rupees
    stt: Rupees
    exchange: Rupees
    sebi: Rupees
    stamp: Rupees
    ipft: Rupees
    gst: Rupees

    @property
    def total(self) -> Rupees:
        return round_rupees(
            self.brokerage + self.stt + self.exchange + self.sebi + self.stamp + self.ipft
            + self.gst
        )  # fmt: skip


def rates_on(day: date) -> ChargeRates:
    applicable = [rates for rates in CHARGE_SCHEDULE if rates.effective_from <= day]
    if not applicable:
        raise InvalidInputError(f"no charge schedule before {CHARGE_SCHEDULE[0].effective_from}")
    return applicable[-1]


def order_charges(
    side: Side, price: Rupees, quantity: int, day: date, plan: BrokeragePlan = GROWW_FNO
) -> OrderCharges:
    """Charges for one executed order of `quantity` units at `price` per unit."""
    if not price.is_finite() or price < 0:  # finite first: comparing NaN raises
        raise InvalidInputError(f"price must be a non-negative amount: {price}")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise InvalidInputError(f"quantity must be a positive int: {quantity!r}")
    rates = rates_on(day)
    turnover = price * quantity
    exchange = turnover * rates.exchange_pct / _PCT
    sebi = turnover * rates.sebi_pct / _PCT
    ipft = turnover * rates.ipft_pct / _PCT
    brokerage = plan.per_order_rupees
    return OrderCharges(
        brokerage=brokerage,
        stt=turnover * rates.stt_sell_pct / _PCT if side is Side.SELL else Decimal(0),
        exchange=exchange,
        sebi=sebi,
        stamp=turnover * rates.stamp_buy_pct / _PCT if side is Side.BUY else Decimal(0),
        ipft=ipft,
        gst=(brokerage + exchange + sebi + ipft) * rates.gst_pct / _PCT,
    )

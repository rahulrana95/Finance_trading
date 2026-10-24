"""Factories for DailyContractBar test data. A 'clean day' passes every quality check."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Any

from fintrade.core.bars import ContractKind, DailyContractBar, OptionType

DAY = date(2026, 10, 23)  # Friday
NEXT_EXPIRY = date(2026, 10, 27)  # Tuesday


def make_bar(**overrides: Any) -> DailyContractBar:
    bar = DailyContractBar(
        trade_date=DAY,
        symbol="NIFTY",
        kind=ContractKind.OPTION,
        expiry=NEXT_EXPIRY,
        strike=Decimal(25800),
        option_type=OptionType.CALL,
        open=Decimal("40"),
        high=Decimal("45"),
        low=Decimal("30"),
        close=Decimal("42.5"),
        settle=Decimal("42.5"),
        last=Decimal("42.6"),
        contracts_traded=1000,
        turnover_rupees=Decimal("2762500"),
        open_interest=650000,
        change_in_oi=6500,
        underlying=Decimal("25200"),
        lot_size=65,
    )
    return replace(bar, **overrides)


def make_future(**overrides: Any) -> DailyContractBar:
    future = make_bar(
        kind=ContractKind.FUTURE,
        expiry=date(2026, 10, 27),
        strike=None,
        option_type=None,
        open=Decimal(25210),
        high=Decimal(25290),
        low=Decimal(25150),
        close=Decimal(25240),
        settle=Decimal(25240),
    )
    return replace(future, **overrides)


def clean_day() -> list[DailyContractBar]:
    return [make_future(), make_bar(), make_bar(option_type=OptionType.PUT)]

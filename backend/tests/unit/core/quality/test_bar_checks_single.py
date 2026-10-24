"""check_bar: one contract at a time."""

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from fintrade.core.quality.bar_checks import IssueCode, Severity, check_bar, contract_key
from tests.support.bars import make_bar, make_future


def _codes(**overrides: Any) -> list[IssueCode]:
    return [issue.code for issue in check_bar(make_bar(**overrides))]


def test_clean_bar_has_no_issues() -> None:
    assert check_bar(make_bar()) == []
    assert check_bar(make_future()) == []


def test_untraded_contract_may_have_zero_ohlc() -> None:
    assert _codes(contracts_traded=0, open=Decimal(0), high=Decimal(0), low=Decimal(0)) == []


@pytest.mark.parametrize("field", ["open", "high", "low", "close", "settle", "turnover_rupees"])
def test_negative_price_is_an_error(field: str) -> None:
    issues = check_bar(make_bar(contracts_traded=0, **{field: Decimal(-1)}))
    assert [(i.code, i.severity) for i in issues] == [(IssueCode.NEGATIVE_VALUE, Severity.ERROR)]
    assert field.split("_", maxsplit=1)[0] in issues[0].detail


@pytest.mark.parametrize("field", ["contracts_traded", "open_interest"])
def test_negative_counts_are_errors(field: str) -> None:
    assert IssueCode.NEGATIVE_VALUE in _codes(**{field: -1})


def test_zero_price_with_trades_is_an_error() -> None:
    assert _codes(low=Decimal(0)) == [IssueCode.ZERO_PRICE_WHEN_TRADED]


def test_high_below_low_is_an_error() -> None:
    assert _codes(high=Decimal(20), low=Decimal(30)) == [IssueCode.HIGH_BELOW_LOW]


@pytest.mark.parametrize(
    ("field", "value"), [("open", "46"), ("open", "29.95"), ("close", "45.05")]
)
def test_open_or_close_outside_range_is_an_error(field: str, value: str) -> None:
    assert _codes(**{field: Decimal(value)}) == [IssueCode.PRICE_OUTSIDE_RANGE]


@pytest.mark.parametrize(("field", "value"), [("open", "45"), ("close", "30")])
def test_prices_exactly_at_high_or_low_are_fine(field: str, value: str) -> None:
    assert _codes(**{field: Decimal(value)}) == []


def test_expiry_before_trade_date_is_an_error() -> None:
    assert _codes(expiry=date(2026, 10, 22)) == [IssueCode.EXPIRY_BEFORE_TRADE_DATE]


def test_expiry_on_trade_date_is_fine() -> None:
    assert _codes(expiry=date(2026, 10, 23)) == []


@pytest.mark.parametrize("strike", ["0", "-50"])
def test_non_positive_strike_is_an_error(strike: str) -> None:
    assert _codes(strike=Decimal(strike)) == [IssueCode.NON_POSITIVE_STRIKE]


def test_issue_carries_day_and_contract() -> None:
    (issue,) = check_bar(make_bar(high=Decimal(1), low=Decimal(2)))
    assert issue.day == date(2026, 10, 23)
    assert issue.contract == "NIFTY 2026-10-27 25800 CE"


def test_contract_key_for_future() -> None:
    assert contract_key(make_future()) == "NIFTY FUT 2026-10-27"

"""AGENTS.md section 1: margin used <= 60% of available margin (after the new trade)."""

from decimal import Decimal

import pytest

from fintrade.core.rules.entry import EntryRule, check_entry
from tests.support.rules import codes, good_account, good_entry

AVAILABLE = Decimal(5_000_000)


def _check(used: int, required: int) -> list[str]:
    account = good_account(margin_used=Decimal(used), margin_available=AVAILABLE)
    return codes(check_entry(good_entry(margin_required=Decimal(required)), account))


def test_exactly_60_percent_after_trade_allowed() -> None:
    assert _check(2_900_000, 100_000) == []  # 3,000,000 / 5,000,000 = 60%


def test_just_over_60_percent_blocked() -> None:
    assert _check(2_900_000, 100_001) == [EntryRule.MARGIN]


def test_well_under_limit_allowed() -> None:
    assert _check(0, 100_000) == []


@pytest.mark.parametrize("available", [0, -1])
def test_no_margin_available_blocked(available: int) -> None:
    account = good_account(margin_available=Decimal(available))
    assert codes(check_entry(good_entry(), account)) == [EntryRule.MARGIN]

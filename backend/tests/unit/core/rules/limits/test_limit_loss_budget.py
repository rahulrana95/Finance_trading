"""AGENTS.md section 1: loss limits, and total max loss <= remaining monthly budget."""

from decimal import Decimal

from fintrade.core.rules.entry import EntryRule, check_entry
from tests.support.rules import codes, good_account, good_entry


def test_loss_limit_hit_blocks_all_entries() -> None:
    assert codes(check_entry(good_entry(), good_account(loss_limit_hit=True))) == [
        EntryRule.LOSS_LIMIT_HIT
    ]


def test_total_max_loss_exactly_at_remaining_budget_allowed() -> None:
    account = good_account(open_max_loss=Decimal(40_000), remaining_monthly_budget=Decimal(58_395))
    assert check_entry(good_entry(max_loss=Decimal(18_395)), account) == []


def test_one_rupee_over_remaining_budget_blocked() -> None:
    account = good_account(open_max_loss=Decimal(40_000), remaining_monthly_budget=Decimal(58_394))
    violations = check_entry(good_entry(max_loss=Decimal(18_395)), account)
    assert codes(violations) == [EntryRule.MAX_LOSS_BUDGET]
    assert "58395 > remaining 58394" in violations[0].detail


def test_no_budget_left_blocks_even_a_small_trade() -> None:
    account = good_account(open_max_loss=Decimal(0), remaining_monthly_budget=Decimal(0))
    assert codes(check_entry(good_entry(max_loss=Decimal(1)), account)) == [
        EntryRule.MAX_LOSS_BUDGET
    ]

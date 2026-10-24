"""AGENTS.md section 1: next week's expiry only (>= 6 days away)."""

from datetime import date

from fintrade.core.rules.entry import EntryRule, check_entry
from tests.support.instruments import EXPIRY
from tests.support.rules import codes, good_account, good_entry


def test_position_on_the_allowed_expiry_passes() -> None:
    assert check_entry(good_entry(entry_expiry=EXPIRY), good_account()) == []


def test_position_on_another_expiry_blocked() -> None:
    entry = good_entry(entry_expiry=date(2026, 11, 9))
    assert codes(check_entry(entry, good_account())) == [EntryRule.EXPIRY]


def test_no_valid_expiry_today_blocks_entry() -> None:
    entry = good_entry(entry_expiry=None)
    assert codes(check_entry(entry, good_account())) == [EntryRule.EXPIRY]

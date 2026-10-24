"""AGENTS.md section 1: open positions <= 5, new positions per day <= 1."""

import pytest

from fintrade.core.rules.entry import EntryRule, check_entry
from tests.support.rules import codes, good_account, good_entry


@pytest.mark.parametrize("open_positions", [0, 3, 4])
def test_up_to_five_open_positions_allowed(open_positions: int) -> None:
    assert check_entry(good_entry(), good_account(open_positions=open_positions)) == []


@pytest.mark.parametrize("open_positions", [5, 6])
def test_sixth_open_position_blocked(open_positions: int) -> None:
    violations = check_entry(good_entry(), good_account(open_positions=open_positions))
    assert codes(violations) == [EntryRule.OPEN_POSITIONS]


def test_first_new_position_today_allowed() -> None:
    assert check_entry(good_entry(), good_account(new_positions_today=0)) == []


@pytest.mark.parametrize("today", [1, 2])
def test_second_new_position_today_blocked(today: int) -> None:
    violations = check_entry(good_entry(), good_account(new_positions_today=today))
    assert codes(violations) == [EntryRule.NEW_POSITIONS_TODAY]

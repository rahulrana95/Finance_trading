"""AGENTS.md section 1: short option delta <= 0.12 at entry, never above."""

from decimal import Decimal

import pytest

from fintrade.core.instruments import Side
from fintrade.core.rules.entry import EntryRule, ProposedEntry, check_entry
from tests.support.instruments import iron_condor
from tests.support.rules import codes, good_account, good_entry


def _with_short_delta(value: Decimal) -> ProposedEntry:
    condor = iron_condor()
    shorts = [leg.contract for leg in condor.legs if leg.side is Side.SELL]
    deltas = {shorts[0]: value, shorts[1]: Decimal("0.05")}
    return good_entry(condor, short_deltas=deltas)


@pytest.mark.parametrize("delta", ["0.12", "-0.12", "0.1199", "0.01"])
def test_at_or_below_limit_allowed(delta: str) -> None:
    assert check_entry(_with_short_delta(Decimal(delta)), good_account()) == []


@pytest.mark.parametrize("delta", ["0.1201", "-0.1201", "0.5"])
def test_above_limit_blocked(delta: str) -> None:
    violations = check_entry(_with_short_delta(Decimal(delta)), good_account())
    assert codes(violations) == [EntryRule.SHORT_DELTA]


@pytest.mark.parametrize("delta", ["NaN", "Infinity"])
def test_non_finite_delta_blocked(delta: str) -> None:
    violations = check_entry(_with_short_delta(Decimal(delta)), good_account())
    assert codes(violations) == [EntryRule.MISSING_DELTA]


def test_missing_delta_blocked_fail_closed() -> None:
    entry = good_entry(short_deltas={})
    assert codes(check_entry(entry, good_account())) == [EntryRule.MISSING_DELTA] * 2


def test_hedge_legs_are_not_checked() -> None:
    condor = iron_condor()
    deltas = {leg.contract: Decimal("0.10") for leg in condor.legs if leg.side is Side.SELL}
    deltas |= {leg.contract: Decimal("0.9") for leg in condor.legs if leg.side is Side.BUY}
    assert check_entry(good_entry(condor, short_deltas=deltas), good_account()) == []

"""A proposed entry and account state that pass every entry rule; tests change one thing."""

from dataclasses import replace
from decimal import Decimal
from typing import Any

from fintrade.core.instruments import Position, Side
from fintrade.core.rules.entry import AccountState, ProposedEntry
from tests.support.instruments import EXPIRY, iron_condor


def good_entry(position: Position | None = None, **overrides: Any) -> ProposedEntry:
    position = position or iron_condor()
    deltas = {leg.contract: Decimal("0.10") for leg in position.legs if leg.side is Side.SELL}
    entry = ProposedEntry(
        position=position,
        short_deltas=deltas,
        max_loss=Decimal(18395),
        margin_required=Decimal(100_000),
        entry_expiry=EXPIRY,
    )
    return replace(entry, **overrides)


def good_account(**overrides: Any) -> AccountState:
    account = AccountState(
        open_positions=2,
        new_positions_today=0,
        open_max_loss=Decimal(40_000),
        remaining_monthly_budget=Decimal(150_000),
        margin_used=Decimal(1_000_000),
        margin_available=Decimal(5_000_000),
        loss_limit_hit=False,
    )
    return replace(account, **overrides)


def codes(violations: list[Any]) -> list[str]:
    return [v.code for v in violations]

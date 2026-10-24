"""Pre-trade checks for a new entry against every AGENTS.md section 1 hard limit.

Every check runs and every violation is reported, so a log shows all the reasons a trade
was blocked. An entry is allowed only when the list is empty (fail closed).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from fintrade.core.errors import RuleViolation
from fintrade.core.instruments import OptionContract, Position, Side
from fintrade.core.limits import HARD_LIMITS, HardLimits
from fintrade.core.money import Rupees

_PCT = Decimal(100)


class EntryRule(StrEnum):
    UNDERLYING = "underlying_not_allowed"
    SHORT_DELTA = "short_delta_too_high"
    MISSING_DELTA = "short_delta_missing"
    EXPIRY = "not_next_weeks_expiry"
    LOSS_LIMIT_HIT = "loss_limit_hit"
    MAX_LOSS_BUDGET = "max_loss_exceeds_budget"
    OPEN_POSITIONS = "too_many_open_positions"
    NEW_POSITIONS_TODAY = "too_many_new_positions_today"
    MARGIN = "margin_limit_exceeded"


@dataclass(frozen=True, slots=True)
class AccountState:
    open_positions: int
    new_positions_today: int
    open_max_loss: Rupees
    remaining_monthly_budget: Rupees
    margin_used: Rupees
    margin_available: Rupees
    loss_limit_hit: bool  # weekly, monthly or yearly limit reached (risk budget tracker)


@dataclass(frozen=True, slots=True)
class ProposedEntry:
    position: Position
    short_deltas: Mapping[OptionContract, Decimal]  # by contract, sign ignored
    max_loss: Rupees  # from core.pnl.risk
    margin_required: Rupees
    entry_expiry: date | None  # from ExpiryCalendar.entry_expiry(today)


def check_entry(
    entry: ProposedEntry, account: AccountState, limits: HardLimits = HARD_LIMITS
) -> list[RuleViolation]:
    return [
        *_underlying(entry, limits),
        *_short_deltas(entry, limits),
        *_expiry(entry),
        *_budget(entry, account),
        *_counts(account, limits),
        *_margin(entry, account, limits),
    ]


def _underlying(entry: ProposedEntry, limits: HardLimits) -> list[RuleViolation]:
    symbols = {leg.contract.symbol for leg in entry.position.legs}
    if symbols != {limits.underlying}:
        return [RuleViolation(EntryRule.UNDERLYING, f"{sorted(symbols)} != {limits.underlying}")]
    return []


def _short_deltas(entry: ProposedEntry, limits: HardLimits) -> list[RuleViolation]:
    found: list[RuleViolation] = []
    for leg in entry.position.legs:
        if leg.side is not Side.SELL:
            continue
        delta = entry.short_deltas.get(leg.contract)
        if delta is None or not delta.is_finite():
            found.append(RuleViolation(EntryRule.MISSING_DELTA, f"no delta for {leg.contract}"))
        elif abs(delta) > limits.max_short_delta:
            detail = f"|{delta}| > {limits.max_short_delta} for {leg.contract}"
            found.append(RuleViolation(EntryRule.SHORT_DELTA, detail))
    return found


def _expiry(entry: ProposedEntry) -> list[RuleViolation]:
    if entry.entry_expiry is None or entry.position.expiry != entry.entry_expiry:
        detail = f"{entry.position.expiry} != allowed {entry.entry_expiry}"
        return [RuleViolation(EntryRule.EXPIRY, detail)]
    return []


def _budget(entry: ProposedEntry, account: AccountState) -> list[RuleViolation]:
    found: list[RuleViolation] = []
    if account.loss_limit_hit:
        found.append(RuleViolation(EntryRule.LOSS_LIMIT_HIT, "a loss limit is hit"))
    total = account.open_max_loss + entry.max_loss
    if total > account.remaining_monthly_budget:
        detail = f"open + new max loss {total} > remaining {account.remaining_monthly_budget}"
        found.append(RuleViolation(EntryRule.MAX_LOSS_BUDGET, detail))
    return found


def _counts(account: AccountState, limits: HardLimits) -> list[RuleViolation]:
    found: list[RuleViolation] = []
    if account.open_positions + 1 > limits.max_open_positions:
        detail = f"{account.open_positions} open, max {limits.max_open_positions}"
        found.append(RuleViolation(EntryRule.OPEN_POSITIONS, detail))
    if account.new_positions_today + 1 > limits.max_new_positions_per_day:
        detail = f"{account.new_positions_today} today, max {limits.max_new_positions_per_day}"
        found.append(RuleViolation(EntryRule.NEW_POSITIONS_TODAY, detail))
    return found


def _margin(entry: ProposedEntry, account: AccountState, limits: HardLimits) -> list[RuleViolation]:
    if account.margin_available <= 0:
        return [RuleViolation(EntryRule.MARGIN, "no margin available")]
    used_pct = (account.margin_used + entry.margin_required) / account.margin_available * _PCT
    if used_pct > limits.max_margin_used_pct:
        detail = f"margin {used_pct:.2f}% > {limits.max_margin_used_pct}%"
        return [RuleViolation(EntryRule.MARGIN, detail)]
    return []

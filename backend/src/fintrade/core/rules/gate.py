"""Last check before any order (AGENTS.md section 2): kill switch, market hours, stale
data, ledger mismatch.

Opening (new risk) is blocked by any of them. Closing is always allowed, because cutting
risk must never be stopped by the tools meant to protect us.
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from enum import StrEnum

from fintrade.core.errors import RuleViolation
from fintrade.core.timezone import ensure_ist

MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)
MAX_DATA_AGE = timedelta(minutes=5)


class OrderIntent(StrEnum):
    OPEN = "open"  # adds risk
    CLOSE = "close"  # reduces risk


class GateRule(StrEnum):
    KILL_SWITCH = "kill_switch_engaged"
    MARKET_CLOSED = "market_closed"
    STALE_DATA = "stale_data"
    LEDGER_MISMATCH = "ledger_mismatch"


@dataclass(frozen=True, slots=True)
class GateInputs:
    intent: OrderIntent
    now: datetime
    is_trading_day: bool
    kill_switch_engaged: bool
    last_data_update: datetime | None
    ledger_matches_broker: bool


def is_market_open(now: datetime, is_trading_day: bool) -> bool:
    clock = ensure_ist(now).time()
    return is_trading_day and MARKET_OPEN <= clock < MARKET_CLOSE


def check_gate(inputs: GateInputs) -> list[RuleViolation]:
    if inputs.intent is OrderIntent.CLOSE:
        return []
    found: list[RuleViolation] = []
    if inputs.kill_switch_engaged:
        found.append(RuleViolation(GateRule.KILL_SWITCH, "kill switch is engaged"))
    if not is_market_open(inputs.now, inputs.is_trading_day):
        found.append(RuleViolation(GateRule.MARKET_CLOSED, f"market closed at {inputs.now}"))
    elif _stale(inputs.last_data_update, inputs.now):
        detail = f"last update {inputs.last_data_update}, older than {MAX_DATA_AGE}"
        found.append(RuleViolation(GateRule.STALE_DATA, detail))
    if not inputs.ledger_matches_broker:
        found.append(RuleViolation(GateRule.LEDGER_MISMATCH, "ledger does not match broker"))
    return found


def _stale(last_update: datetime | None, now: datetime) -> bool:
    if last_update is None:
        return True
    age = ensure_ist(now) - ensure_ist(last_update)
    return age > MAX_DATA_AGE or age < timedelta(0)  # data from the future is also wrong

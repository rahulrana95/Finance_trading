"""Tunable strategy parameters (RULES.md). Unlike HARD_LIMITS these are not locked: the
walk-forward backtest proposes values and the owner approves them (DECISIONS.md).

Defaults are conservative placeholders until the backtest sets them.
"""

from dataclasses import dataclass
from datetime import time
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class EntryFilterConfig:
    entry_window_start: time = time(10, 0)  # RULES.md section 3
    entry_window_end: time = time(15, 0)  # entries must be before this time
    min_credit_pct_of_width: Decimal = Decimal(10)  # backtest tests 5-15%
    vix_min: Decimal | None = None  # None = band not applied yet
    vix_max: Decimal | None = None
    event_blackout: bool = True  # no entry if an event is today or next trading day


DEFAULT_ENTRY_FILTERS = EntryFilterConfig()

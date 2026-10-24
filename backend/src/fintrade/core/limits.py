"""Hard trading limits from AGENTS.md section 1 (locked).

These values may only change when the owner changes AGENTS.md. A test compares this module
with the AGENTS.md table, so the two cannot drift apart.
"""

from dataclasses import dataclass
from datetime import time
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class HardLimits:
    underlying: str
    max_short_delta: Decimal
    min_days_to_expiry_at_entry: int
    exit_cutoff_day_before_expiry: time
    max_weekly_loss_pct: Decimal
    max_monthly_drawdown_pct: Decimal
    max_yearly_drawdown_pct: Decimal
    max_open_positions: int
    max_new_positions_per_day: int
    max_margin_used_pct: Decimal
    max_adjustments_per_position: int


HARD_LIMITS = HardLimits(
    underlying="NIFTY",
    max_short_delta=Decimal("0.12"),
    min_days_to_expiry_at_entry=6,
    exit_cutoff_day_before_expiry=time(15, 0),
    max_weekly_loss_pct=Decimal(1),
    max_monthly_drawdown_pct=Decimal(3),
    max_yearly_drawdown_pct=Decimal(5),
    max_open_positions=5,
    max_new_positions_per_day=1,
    max_margin_used_pct=Decimal(60),
    max_adjustments_per_position=1,
)

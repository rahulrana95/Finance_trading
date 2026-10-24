"""Weekly loss, monthly / yearly drawdown, and the budget left for new risk.

Definitions (owner-approved interpretation of AGENTS.md section 1):
- equity = cumulative realized P&L + open mark-to-market (relative to trading capital)
- weekly loss = equity now - equity at the end of the previous ISO week (Mon-Sun)
- monthly / yearly drawdown = highest equity since the end of the previous calendar
  month / year (including that starting level) minus equity now
- a limit is HIT when the loss / drawdown reaches the limit (at the limit counts)
- remaining monthly budget = monthly limit - drawdown of REALIZED equity this month,
  never more than what is left of the yearly limit. Open positions are counted by their
  worst-case max loss against this budget (core.rules.entry), not by their open P&L, so
  they are not counted twice.
"""

from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from fintrade.core.errors import InvalidInputError
from fintrade.core.limits import HARD_LIMITS, HardLimits
from fintrade.core.money import Rupees

_PCT = Decimal(100)


@dataclass(frozen=True, slots=True)
class DailyPnl:
    """End-of-day state. `realized_total` is cumulative since trading began."""

    day: date
    realized_total: Rupees
    open_mtm: Rupees

    @property
    def equity(self) -> Rupees:
        return self.realized_total + self.open_mtm


@dataclass(frozen=True, slots=True)
class BudgetStatus:
    week_pnl: Rupees
    month_drawdown: Rupees
    year_drawdown: Rupees
    weekly_hit: bool
    monthly_hit: bool
    yearly_hit: bool
    remaining_monthly_budget: Rupees

    @property
    def any_limit_hit(self) -> bool:
        return self.weekly_hit or self.monthly_hit or self.yearly_hit


def budget_status(
    capital: Rupees, history: Sequence[DailyPnl], limits: HardLimits = HARD_LIMITS
) -> BudgetStatus:
    """Status as of the last entry in `history` (sorted by day, one entry per day)."""
    _validate(capital, history)
    today = history[-1]
    week_limit = capital * limits.max_weekly_loss_pct / _PCT
    month_limit = capital * limits.max_monthly_drawdown_pct / _PCT
    year_limit = capital * limits.max_yearly_drawdown_pct / _PCT

    week_pnl = today.equity - _baseline(history, _iso_week, lambda p: p.equity)
    month_dd = _drawdown(history, _month, lambda p: p.equity)
    year_dd = _drawdown(history, _year, lambda p: p.equity)
    realized_month_dd = _drawdown(history, _month, lambda p: p.realized_total)
    realized_year_dd = _drawdown(history, _year, lambda p: p.realized_total)
    remaining = min(month_limit - realized_month_dd, year_limit - realized_year_dd)
    return BudgetStatus(
        week_pnl=week_pnl,
        month_drawdown=month_dd,
        year_drawdown=year_dd,
        weekly_hit=-week_pnl >= week_limit,
        monthly_hit=month_dd >= month_limit,
        yearly_hit=year_dd >= year_limit,
        remaining_monthly_budget=max(remaining, Decimal(0)),
    )


def _validate(capital: Rupees, history: Sequence[DailyPnl]) -> None:
    if not capital.is_finite() or capital <= 0:
        raise InvalidInputError(f"capital must be positive: {capital}")
    if not history:
        raise InvalidInputError("history is empty")
    days = [p.day for p in history]
    if days != sorted(set(days)):
        raise InvalidInputError("history must be sorted with one entry per day")


def _iso_week(day: date) -> Hashable:
    iso = day.isocalendar()
    return (iso.year, iso.week)


def _month(day: date) -> Hashable:
    return (day.year, day.month)


def _year(day: date) -> Hashable:
    return day.year


def _baseline(
    history: Sequence[DailyPnl],
    period: Callable[[date], Hashable],
    value: Callable[[DailyPnl], Rupees],
) -> Rupees:
    """Value at the end of the previous period (0 before any history)."""
    current = period(history[-1].day)
    before = [p for p in history if period(p.day) != current]  # sorted: earlier periods
    return value(before[-1]) if before else Decimal(0)


def _drawdown(
    history: Sequence[DailyPnl],
    period: Callable[[date], Hashable],
    value: Callable[[DailyPnl], Rupees],
) -> Rupees:
    current = period(history[-1].day)
    in_period = [value(p) for p in history if period(p.day) == current]
    peak = max([_baseline(history, period, value), *in_period])
    return peak - value(history[-1])

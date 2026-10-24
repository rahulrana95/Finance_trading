"""Backtest metrics and the text report.

AGENTS.md section 5: max drawdown, worst week, worst month and the number of trades are
always shown next to the return. P&L is measured against a fixed trading capital (no
compounding), so the annualized return is simple, not compound.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from fintrade.backtest.trades import ClosedTrade
from fintrade.core.errors import InvalidInputError
from fintrade.core.limits import HARD_LIMITS
from fintrade.core.money import Rupees
from fintrade.core.risk.budget import DailyPnl

_PCT = Decimal(100)
_ZERO = Decimal(0)
_DAYS_PER_YEAR = 365


@dataclass(frozen=True, slots=True)
class PeriodPnl:
    label: str  # "2026-W40" or "2026-09"
    pnl: Rupees


@dataclass(frozen=True, slots=True)
class Metrics:
    capital: Rupees
    start: date
    end: date
    net_pnl: Rupees
    return_pct: Decimal
    annualized_return_pct: Decimal
    max_drawdown: Rupees
    max_drawdown_pct: Decimal
    worst_week: PeriodPnl
    worst_month: PeriodPnl
    weeks_at_or_over_loss_limit: int
    trades: int
    wins: int
    losses: int
    win_rate_pct: Decimal | None
    avg_win: Rupees | None
    avg_loss: Rupees | None
    profit_factor: Decimal | None  # gross wins / gross losses
    total_costs: Rupees


def compute_metrics(
    capital: Rupees, daily: Sequence[DailyPnl], closed: Sequence[ClosedTrade]
) -> Metrics:
    _validate(capital, daily)
    start, end = daily[0].day, daily[-1].day
    net = daily[-1].equity
    return_pct = net / capital * _PCT
    max_dd = _max_drawdown(daily)
    weeks = _period_pnl(daily, _week_label)
    week_limit = capital * HARD_LIMITS.max_weekly_loss_pct / _PCT
    pnls = [t.net_pnl for t in closed]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    return Metrics(
        capital=capital,
        start=start,
        end=end,
        net_pnl=net,
        return_pct=return_pct,
        annualized_return_pct=return_pct * _DAYS_PER_YEAR / ((end - start).days + 1),
        max_drawdown=max_dd,
        max_drawdown_pct=max_dd / capital * _PCT,
        worst_week=min(weeks, key=_pnl),
        worst_month=min(_period_pnl(daily, _month_label), key=_pnl),
        weeks_at_or_over_loss_limit=sum(1 for w in weeks if -w.pnl >= week_limit),
        trades=len(pnls),
        wins=len(wins),
        losses=len(losses),
        win_rate_pct=Decimal(len(wins)) / len(pnls) * _PCT if pnls else None,
        avg_win=_mean(wins),
        avg_loss=_mean(losses),
        profit_factor=sum(wins, start=_ZERO) / -sum(losses, start=_ZERO) if losses else None,
        total_costs=sum((t.trade.entry_costs + t.exit_costs for t in closed), start=_ZERO),
    )


def format_report(m: Metrics) -> str:
    win_rate = "n/a" if m.win_rate_pct is None else f"{m.win_rate_pct:.1f}%"
    return "\n".join(
        [
            f"Backtest {m.start} to {m.end}, capital ₹{m.capital:,.0f}",
            f"Return: {m.return_pct:+.2f}% (₹{m.net_pnl:,.0f}), "
            f"simple annualized {m.annualized_return_pct:+.2f}%",
            f"Max drawdown: {m.max_drawdown_pct:.2f}% (₹{m.max_drawdown:,.0f})",
            f"Worst week: {m.worst_week.label} ₹{m.worst_week.pnl:,.0f}; "
            f"weeks at or over the loss limit: {m.weeks_at_or_over_loss_limit}",
            f"Worst month: {m.worst_month.label} ₹{m.worst_month.pnl:,.0f}",
            f"Trades: {m.trades} (wins {m.wins}, losses {m.losses}), Win rate: {win_rate}",
            f"Costs paid: ₹{m.total_costs:,.0f}",
            "A backtest is not a guarantee of future results.",
        ]
    )


def _validate(capital: Rupees, daily: Sequence[DailyPnl]) -> None:
    if not capital.is_finite() or capital <= 0:
        raise InvalidInputError(f"capital must be positive: {capital}")
    days = [p.day for p in daily]
    if not days or days != sorted(set(days)):
        raise InvalidInputError("daily P&L must be non-empty, sorted, one entry per day")


def _max_drawdown(daily: Sequence[DailyPnl]) -> Rupees:
    peak, worst = _ZERO, _ZERO  # equity starts at 0 against the capital
    for p in daily:
        peak = max(peak, p.equity)
        worst = max(worst, peak - p.equity)
    return worst


def _period_pnl(daily: Sequence[DailyPnl], label: Callable[[date], str]) -> list[PeriodPnl]:
    """Equity change over each period: end-of-period equity minus the previous one."""
    ends: dict[str, Rupees] = {}
    for p in daily:
        ends[label(p.day)] = p.equity  # sorted input: last write is the period end
    result, previous = [], _ZERO
    for name, equity in ends.items():
        result.append(PeriodPnl(name, equity - previous))
        previous = equity
    return result


def _week_label(day: date) -> str:
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _month_label(day: date) -> str:
    return f"{day.year}-{day.month:02d}"


def _pnl(period: PeriodPnl) -> Rupees:
    return period.pnl


def _mean(values: list[Rupees]) -> Rupees | None:
    return sum(values, start=_ZERO) / len(values) if values else None

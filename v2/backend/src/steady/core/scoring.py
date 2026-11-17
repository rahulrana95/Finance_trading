"""Stability, financial and evidence scores (v2/docs/DESIGN.md sections 3.2 to 3.4)."""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from steady.constants import (
    DATA_PROBLEM_PENALTY,
    DRAWDOWN_RANGE,
    EVIDENCE_WEIGHTS,
    FINANCIAL_WEIGHTS,
    FINANCIAL_YEARS,
    HISTORY_YEARS_RANGE,
    LONGEST_RECOVERY_RANGE,
    MAX_DEBT_TO_EQUITY,
    MIN_FALLS_TO_JUDGE,
    NEED_DEBT,
    NEED_FEW_FALLS,
    NEED_PLEDGE,
    NEED_PROFIT_ENDS,
    NEED_PROFIT_YEARS,
    NEED_REVENUE_YEARS,
    NEED_SHORT_HISTORY,
    OPEN_FALL_LIMIT_DAYS,
    QUICK_RECOVERY_RANGE,
    STABILITY_WEIGHTS,
)


@dataclass(frozen=True)
class StabilityInput:
    falls: int
    recovered_within_pct: float | None
    longest_recovery_days: int
    open_fall_days: int
    max_drawdown_pct: float
    history_years: float


@dataclass(frozen=True)
class FinYear:
    period: str
    revenue: float | None
    net_profit: float | None


@dataclass(frozen=True)
class FinancialInput:
    years: Sequence[FinYear]
    debt_to_equity: float | None
    promoter_pledge_pct: float | None
    is_lender: bool


def _half_up(value: float) -> int:
    """Round .5 upwards, so 72.5 is 73 (Python's round() would give 72)."""
    return math.floor(value + 0.5)


def _linear(value: float, zero_at: float, full_at: float) -> float:
    """0 at `zero_at`, 1 at `full_at`, clamped; works in either direction."""
    return min(1.0, max(0.0, (value - zero_at) / (full_at - zero_at)))


def stability_score(m: StabilityInput) -> tuple[int, list[str]]:
    w = STABILITY_WEIGHTS
    needs: list[str] = []
    quick = w["quick"] * _linear(m.recovered_within_pct or 0.0, *QUICK_RECOVERY_RANGE)
    no_long = w["no_long"] * _linear(m.longest_recovery_days, *LONGEST_RECOVERY_RANGE)
    if m.falls < MIN_FALLS_TO_JUDGE:
        quick, no_long = min(quick, w["quick"] / 2), min(no_long, w["no_long"] / 2)
        needs.append(NEED_FEW_FALLS)
    nothing_open = 0.0 if m.open_fall_days > OPEN_FALL_LIMIT_DAYS else w["nothing_open"]
    shallow = w["shallow"] * _linear(m.max_drawdown_pct, *DRAWDOWN_RANGE)
    history = w["history"] * _linear(m.history_years, *HISTORY_YEARS_RANGE)
    if m.history_years < HISTORY_YEARS_RANGE[1]:
        needs.append(NEED_SHORT_HISTORY)
    return _half_up(quick + no_long + nothing_open + shallow + history), needs


def _missing(years: Sequence[FinYear], field: str) -> list[str]:
    return [y.period for y in years if getattr(y, field) is None]


def _grew(first: float | None, last: float | None) -> bool | None:
    return None if first is None or last is None else last > first


def financial_score(f: FinancialInput) -> tuple[int, list[str]]:
    w = FINANCIAL_WEIGHTS
    years = f.years
    enough = len(years) >= FINANCIAL_YEARS
    no_revenue, no_profit = _missing(years, "revenue"), _missing(years, "net_profit")
    revenue_need = f"Revenue for {', '.join(no_revenue)}" if no_revenue else NEED_REVENUE_YEARS
    profit_need = f"Net profit for {', '.join(no_profit)}" if no_profit else NEED_PROFIT_YEARS

    # (weight, result or None when it cannot be judged, what is needed to judge it)
    checks: list[tuple[float, bool | None, str]] = [
        (
            w["revenue"],
            _grew(years[0].revenue, years[-1].revenue) if enough else None,
            revenue_need,
        ),
        (
            w["profit_every_year"],
            all((y.net_profit or 0) > 0 for y in years) if enough and not no_profit else None,
            profit_need,
        ),
        (
            w["profit_growth"],
            _grew(years[0].net_profit, years[-1].net_profit) if enough else None,
            NEED_PROFIT_ENDS,
        ),
        (
            w["pledge"],
            None if f.promoter_pledge_pct is None else f.promoter_pledge_pct == 0,
            NEED_PLEDGE,
        ),
    ]
    if not f.is_lender:
        debt_ok = None if f.debt_to_equity is None else f.debt_to_equity < MAX_DEBT_TO_EQUITY
        checks.insert(3, (w["debt"], debt_ok, NEED_DEBT))

    earned = sum(weight for weight, result, _ in checks if result)
    possible = sum(weight for weight, _, _ in checks)
    needs = [need for _, result, need in checks if result is None]
    if no_revenue and revenue_need not in needs:
        needs.append(revenue_need)  # a missing middle year does not block the growth check
    return _half_up(100 * earned / possible), list(dict.fromkeys(needs))


def evidence(stability: int, financial: int, problems: int) -> tuple[int, int]:
    """Returns (data quality, evidence score). Not a probability."""
    data_quality = _half_up(max(0.0, 100 - DATA_PROBLEM_PENALTY * problems))
    ws, wf, wd = EVIDENCE_WEIGHTS
    return data_quality, _half_up(ws * stability + wf * financial + wd * data_quality)

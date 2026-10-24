from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from fintrade.core.errors import InvalidInputError
from fintrade.core.limits import HARD_LIMITS
from fintrade.core.risk.budget import DailyPnl, budget_status

CAPITAL = Decimal(5_000_000)  # limits: week 50K, month 1.5L, year 2.5L


def _day(d: date, realized: int, open_mtm: int = 0) -> DailyPnl:
    return DailyPnl(d, Decimal(realized), Decimal(open_mtm))


def test_first_day_has_full_budget() -> None:
    s = budget_status(CAPITAL, [_day(date(2026, 10, 26), 0)])
    assert (s.week_pnl, s.month_drawdown, s.year_drawdown) == (Decimal(0),) * 3
    assert s.remaining_monthly_budget == Decimal(150_000)
    assert not s.any_limit_hit


@pytest.mark.parametrize(("equity_now", "hit"), [(-40_000, True), (-39_999, False)])
def test_weekly_loss_hit_exactly_at_one_percent(equity_now: int, hit: bool) -> None:
    history = [_day(date(2026, 10, 23), 10_000), _day(date(2026, 10, 28), 0, equity_now)]
    s = budget_status(CAPITAL, history)
    assert s.week_pnl == equity_now - 10_000
    assert s.weekly_hit is hit


def test_monthly_drawdown_measured_from_the_peak() -> None:
    history = [
        _day(date(2026, 9, 30), 20_000),  # previous month end: the starting level
        _day(date(2026, 10, 9), 60_000),  # peak
        _day(date(2026, 10, 23), -90_000),
    ]
    s = budget_status(CAPITAL, history)
    assert s.month_drawdown == Decimal(150_000)
    assert s.monthly_hit


def test_starting_level_counts_as_a_peak() -> None:
    history = [_day(date(2026, 9, 30), 100_000), _day(date(2026, 10, 1), 0)]
    assert budget_status(CAPITAL, history).month_drawdown == Decimal(100_000)


def test_yearly_drawdown_from_previous_year_end() -> None:
    history = [_day(date(2025, 12, 31), 300_000), _day(date(2026, 10, 23), 50_000)]
    s = budget_status(CAPITAL, history)
    assert s.year_drawdown == Decimal(250_000)
    assert s.yearly_hit


def test_remaining_budget_uses_realized_equity_only() -> None:
    history = [_day(date(2026, 9, 30), 0), _day(date(2026, 10, 23), -50_000, -80_000)]
    s = budget_status(CAPITAL, history)
    assert s.remaining_monthly_budget == Decimal(100_000)  # open -80K counted via max loss
    assert s.month_drawdown == Decimal(130_000)  # but open P&L does count for the limit


def test_remaining_budget_capped_by_what_is_left_of_the_year() -> None:
    history = [
        _day(date(2025, 12, 31), 0),
        _day(date(2026, 9, 30), -220_000),
        _day(date(2026, 10, 23), -220_000),
    ]
    assert budget_status(CAPITAL, history).remaining_monthly_budget == Decimal(30_000)


def test_remaining_budget_never_negative() -> None:
    history = [_day(date(2026, 9, 30), 0), _day(date(2026, 10, 23), -200_000)]
    assert budget_status(CAPITAL, history).remaining_monthly_budget == 0


def test_iso_week_spans_new_year() -> None:
    # Thu 2026-12-31 and Fri 2027-01-01 are both in ISO week 2026-W53.
    history = [
        _day(date(2026, 12, 25), 0),
        _day(date(2026, 12, 31), -30_000),
        _day(date(2027, 1, 1), -50_000),
    ]
    s = budget_status(CAPITAL, history)
    assert s.week_pnl == Decimal(-50_000)
    assert s.weekly_hit
    assert s.month_drawdown == Decimal(20_000)  # new month starts from -30K


@pytest.mark.parametrize("capital", [Decimal(0), Decimal(-1), Decimal("NaN")])
def test_bad_capital_rejected(capital: Decimal) -> None:
    with pytest.raises(InvalidInputError, match="capital must be positive"):
        budget_status(capital, [_day(date(2026, 10, 23), 0)])


def test_empty_history_rejected() -> None:
    with pytest.raises(InvalidInputError, match=r"^history is empty$"):
        budget_status(CAPITAL, [])


@pytest.mark.parametrize(
    "days", [[date(2026, 10, 23), date(2026, 10, 22)], [date(2026, 10, 23), date(2026, 10, 23)]]
)
def test_unsorted_or_duplicate_days_rejected(days: list[date]) -> None:
    with pytest.raises(InvalidInputError, match=r"^history must be sorted with one entry per day$"):
        budget_status(CAPITAL, [_day(d, 0) for d in days])


@given(
    st.lists(
        st.tuples(st.integers(-300_000, 300_000), st.integers(-50_000, 50_000)),
        min_size=1,
        max_size=40,
    )
)
def test_drawdowns_non_negative_and_budget_bounded(points: list[tuple[int, int]]) -> None:
    history = [
        _day(date.fromordinal(date(2026, 1, 1).toordinal() + i * 3), realized, open_mtm)
        for i, (realized, open_mtm) in enumerate(points)
    ]
    s = budget_status(CAPITAL, history)
    assert s.month_drawdown >= 0
    assert s.year_drawdown >= 0
    assert 0 <= s.remaining_monthly_budget <= Decimal(150_000)


def test_limits_scale_with_the_configured_percentages() -> None:
    limits = replace(HARD_LIMITS, max_weekly_loss_pct=Decimal(2))
    history = [_day(date(2026, 10, 23), 0), _day(date(2026, 10, 28), -99_999)]
    assert not budget_status(CAPITAL, history, limits).weekly_hit  # limit is 100K at 2%
    history[-1] = _day(date(2026, 10, 28), -100_000)
    assert budget_status(CAPITAL, history, limits).weekly_hit


def test_tiny_positive_capital_is_valid() -> None:
    assert budget_status(
        Decimal(1), [_day(date(2026, 10, 23), 0)]
    ).remaining_monthly_budget == Decimal("0.03")

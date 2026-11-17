"""Stability, financial and evidence scores, and buy zones (TEST_PLAN F01-F17, Z01-Z06)."""

import pytest

from steady.core.scoring import (
    FinancialInput,
    FinYear,
    StabilityInput,
    evidence,
    financial_score,
    stability_score,
)
from steady.core.zones import level_price, zone

FULL = StabilityInput(
    falls=11,
    recovered_within_pct=90.0,
    longest_recovery_days=252,
    open_fall_days=0,
    max_drawdown_pct=30.0,
    history_years=8.0,
)


def years(profit: list[float | None], revenue: list[float | None] | None = None) -> list[FinYear]:
    revenue = revenue or [1, 2, 3, 4, 5]
    return [FinYear(f"FY{2022 + i}", revenue[i], p) for i, p in enumerate(profit)]


GOOD = FinancialInput(
    years([1, 2, 3, 4, 5]), debt_to_equity=0.2, promoter_pledge_pct=0.0, is_lender=False
)


def with_(base: StabilityInput, **changes: float | None) -> StabilityInput:
    return StabilityInput(**{**base.__dict__, **changes})


def test_full_marks_when_every_part_is_at_its_best():  # F10
    assert stability_score(FULL) == (100, [])


def test_quick_recovery_marks_scale_between_50_and_90_percent():  # F11, F12
    assert stability_score(with_(FULL, recovered_within_pct=50.0))[0] == 65
    assert stability_score(with_(FULL, recovered_within_pct=70.0))[0] == 83


def test_few_falls_cap_the_recovery_parts_and_ask_for_data():  # F13
    score, needs = stability_score(with_(FULL, falls=3))
    assert score == 73
    assert needs == ["Few past falls to judge recovery"]


def test_no_falls_at_all_is_treated_as_unknown_not_perfect():
    score, needs = stability_score(with_(FULL, falls=0, recovered_within_pct=None))
    assert score == 55
    assert "Few past falls to judge recovery" in needs


def test_an_old_open_fall_loses_its_part():  # F14
    assert stability_score(with_(FULL, open_fall_days=200))[0] == 85


def test_short_history_is_flagged():
    score, needs = stability_score(with_(FULL, history_years=5.5))
    assert needs == ["Fewer than 8 years of price history"]
    assert score == 93


def test_the_worst_case_is_zero():
    worst = StabilityInput(9, 0.0, 2000, 900, 95.0, 1.0)
    assert stability_score(worst)[0] == 0


def test_financial_full_marks():  # F01
    assert financial_score(GOOD) == (100, [])


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"years": years([-1, 2, 3, 4, 5])}, 75),  # F02 one loss-making year
        ({"years": years([1, 2, 3, 4, 5], [9, 2, 3, 4, 5])}, 80),  # F03 revenue lower
        ({"debt_to_equity": 1.0}, 80),  # F04 debt at the limit fails
        ({"promoter_pledge_pct": 0.1}, 85),  # F06 any pledge fails
        ({"years": years([5, 2, 3, 4, 1])}, 80),  # profit lower than 4 years ago
    ],
)
def test_each_failed_check_costs_its_weight(change: dict[str, object], expected: int):
    assert financial_score(FinancialInput(**{**GOOD.__dict__, **change}))[0] == expected


def test_a_lender_skips_the_debt_check_and_rescales():  # F05
    lender = FinancialInput(
        GOOD.years, debt_to_equity=None, promoter_pledge_pct=0.0, is_lender=True
    )
    assert financial_score(lender) == (100, [])


def test_missing_years_are_named():  # F07
    score, needs = financial_score(FinancialInput(years([1, None, None, 4, 5]), 0.2, 0.0, False))
    assert score == 75
    assert "Net profit for FY2023, FY2024" in needs


def test_missing_revenue_is_reported_even_when_growth_can_be_judged():
    _, needs = financial_score(
        FinancialInput(years([1, 2, 3, 4, 5], [1, None, 3, 4, 5]), 0.2, 0.0, False)
    )
    assert needs == ["Revenue for FY2023"]


def test_growth_cannot_be_judged_without_the_first_or_latest_year():
    assert (
        financial_score(
            FinancialInput(years([1, 2, 3, 4, 5], [None, 2, 3, 4, 5]), 0.2, 0.0, False)
        )[0]
        == 80
    )
    assert financial_score(FinancialInput(years([None, 2, 3, 4, 5]), 0.2, 0.0, False))[0] == 55
    assert financial_score(FinancialInput(years([1, 2, 3, 4, None]), 0.2, 0.0, False))[0] == 55


def test_no_data_scores_zero_and_lists_everything():  # F08
    score, needs = financial_score(FinancialInput([], None, None, False))
    assert score == 0
    assert needs == [
        "Five years of revenue",
        "Five years of net profit",
        "Net profit for the first and latest year",
        "Debt and equity",
        "Promoter pledge",
    ]


def test_evidence_weights_and_data_penalty():  # F15, F16, F17
    assert evidence(80, 60, problems=2) == (60, 70)
    assert evidence(100, 100, problems=9) == (0, 80)


def test_zone_boundaries():  # Z01-Z05
    assert [zone(b) for b in (0.0, 9.9, 10.0, 25.0, 35.0)] == [0, 0, 1, 2, 3]


def test_level_prices():  # Z06
    assert [level_price(1598.1, p) for p in (10, 20, 30, 40)] == [1438.29, 1278.48, 1118.67, 958.86]

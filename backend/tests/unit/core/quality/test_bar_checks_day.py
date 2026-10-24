"""check_day: whole-day checks (duplicates, coverage, pairs, expiries)."""

from datetime import date
from decimal import Decimal

from fintrade.core.bars import OptionType
from fintrade.core.quality.bar_checks import IssueCode, Severity, check_day
from tests.support.bars import DAY, clean_day, make_bar, make_future


def _codes(bars: list) -> list[IssueCode]:  # type: ignore[type-arg]
    return [issue.code for issue in check_day(DAY, bars)]


def test_clean_day_passes() -> None:
    assert check_day(DAY, clean_day()) == []


def test_duplicate_contract_is_an_error() -> None:
    issues = check_day(DAY, [*clean_day(), make_bar()])
    assert [(i.code, i.severity, i.detail) for i in issues] == [
        (IssueCode.DUPLICATE_CONTRACT, Severity.ERROR, "2 rows")
    ]


def test_missing_futures_is_an_error() -> None:
    assert _codes([make_bar(), make_bar(option_type=OptionType.PUT)]) == [IssueCode.NO_FUTURES]


def test_missing_options_is_an_error() -> None:
    assert _codes([make_future()]) == [IssueCode.NO_OPTIONS]


def test_empty_day_reports_both() -> None:
    assert _codes([]) == [IssueCode.NO_FUTURES, IssueCode.NO_OPTIONS]


def test_strike_with_only_one_side_is_a_warning() -> None:
    bars = [*clean_day(), make_bar(strike=Decimal(26000))]
    issues = check_day(DAY, bars)
    assert [(i.code, i.severity, i.contract) for i in issues] == [
        (IssueCode.MISSING_CALL_OR_PUT, Severity.WARNING, "2026-10-27 26000")
    ]
    assert "CE" in issues[0].detail


def test_one_sided_strike_on_far_expiry_is_ignored() -> None:
    far = date(2026, 11, 27)  # 35 days after DAY: still checked
    beyond = date(2026, 11, 28)  # 36 days: ignored
    assert _codes([*clean_day(), make_bar(expiry=far)]) == [IssueCode.MISSING_CALL_OR_PUT]
    assert _codes([*clean_day(), make_bar(expiry=beyond)]) == []


def test_no_weekly_expiry_within_8_days_is_a_warning() -> None:
    far = date(2026, 11, 3)  # 11 days after DAY
    bars = [make_future(), make_bar(expiry=far), make_bar(expiry=far, option_type=OptionType.PUT)]
    assert _codes(bars) == [IssueCode.NO_NEAR_WEEKLY_EXPIRY]


def test_expiry_exactly_8_days_away_is_fine() -> None:
    edge = date(2026, 10, 31)
    bars = [make_future(), make_bar(expiry=edge), make_bar(expiry=edge, option_type=OptionType.PUT)]
    assert _codes(bars) == []


def test_bar_level_issues_are_included() -> None:
    bars = [*clean_day(), make_bar(strike=Decimal(25900), high=Decimal(1), low=Decimal(2)),
            make_bar(strike=Decimal(25900), option_type=OptionType.PUT)]  # fmt: skip
    assert _codes(bars) == [IssueCode.HIGH_BELOW_LOW]

"""Data-quality checks for one trading day of `DailyContractBar` rows. Pure functions.

ERROR = data must not be used as-is. WARNING = suspicious, review it.
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum

from fintrade.core.bars import ContractKind, DailyContractBar, OptionType

MAX_DAYS_TO_NEAREST_WEEKLY_EXPIRY = 8
# Call/put pairing is only checked where we trade; far-dated strikes are often one-sided.
MAX_DAYS_FOR_PAIR_CHECK = 35
_ZERO = Decimal(0)


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class IssueCode(StrEnum):
    NEGATIVE_VALUE = "negative_value"
    HIGH_BELOW_LOW = "high_below_low"
    PRICE_OUTSIDE_RANGE = "price_outside_range"
    ZERO_PRICE_WHEN_TRADED = "zero_price_when_traded"
    EXPIRY_BEFORE_TRADE_DATE = "expiry_before_trade_date"
    NON_POSITIVE_STRIKE = "non_positive_strike"
    DUPLICATE_CONTRACT = "duplicate_contract"
    NO_OPTIONS = "no_options"
    NO_FUTURES = "no_futures"
    MISSING_CALL_OR_PUT = "missing_call_or_put"
    NO_NEAR_WEEKLY_EXPIRY = "no_near_weekly_expiry"


@dataclass(frozen=True, slots=True)
class Issue:
    day: date
    severity: Severity
    code: IssueCode
    contract: str
    detail: str


def contract_key(bar: DailyContractBar) -> str:
    if bar.kind is ContractKind.FUTURE:
        return f"{bar.symbol} FUT {bar.expiry}"
    return f"{bar.symbol} {bar.expiry} {bar.strike} {bar.option_type}"


def check_day(day: date, bars: Sequence[DailyContractBar]) -> list[Issue]:
    issues = [issue for bar in bars for issue in check_bar(bar)]
    issues += _duplicates(day, bars)
    issues += _coverage(day, bars)
    return issues


def check_bar(bar: DailyContractBar) -> list[Issue]:
    found: list[tuple[Severity, IssueCode, str]] = []
    numbers = {
        "open": bar.open, "high": bar.high, "low": bar.low, "close": bar.close,
        "settle": bar.settle, "contracts_traded": Decimal(bar.contracts_traded),
        "open_interest": Decimal(bar.open_interest), "turnover": bar.turnover_rupees,
    }  # fmt: skip
    negative = [name for name, value in numbers.items() if value < _ZERO]
    if negative:
        found.append((Severity.ERROR, IssueCode.NEGATIVE_VALUE, f"negative: {negative}"))
    if bar.contracts_traded > 0:
        found += _traded_price_checks(bar)
    if bar.expiry < bar.trade_date:
        found.append((Severity.ERROR, IssueCode.EXPIRY_BEFORE_TRADE_DATE, f"expiry {bar.expiry}"))
    if bar.strike is not None and bar.strike <= _ZERO:
        found.append((Severity.ERROR, IssueCode.NON_POSITIVE_STRIKE, f"strike {bar.strike}"))
    key = contract_key(bar)
    return [Issue(bar.trade_date, sev, code, key, detail) for sev, code, detail in found]


def _traded_price_checks(bar: DailyContractBar) -> list[tuple[Severity, IssueCode, str]]:
    if min(bar.open, bar.high, bar.low, bar.close) <= _ZERO:
        return [(Severity.ERROR, IssueCode.ZERO_PRICE_WHEN_TRADED, "zero OHLC with trades")]
    if bar.high < bar.low:
        return [(Severity.ERROR, IssueCode.HIGH_BELOW_LOW, f"high {bar.high} < low {bar.low}")]
    outside = [
        name
        for name, value in (("open", bar.open), ("close", bar.close))
        if not bar.low <= value <= bar.high
    ]
    if outside:
        detail = f"{outside} outside [{bar.low}, {bar.high}]"
        return [(Severity.ERROR, IssueCode.PRICE_OUTSIDE_RANGE, detail)]
    return []


def _duplicates(day: date, bars: Iterable[DailyContractBar]) -> list[Issue]:
    counts = Counter(contract_key(bar) for bar in bars)
    return [
        Issue(day, Severity.ERROR, IssueCode.DUPLICATE_CONTRACT, key, f"{count} rows")
        for key, count in counts.items()
        if count > 1
    ]


def _coverage(day: date, bars: Sequence[DailyContractBar]) -> list[Issue]:
    options = [bar for bar in bars if bar.kind is ContractKind.OPTION]
    issues: list[Issue] = []
    if not any(bar.kind is ContractKind.FUTURE for bar in bars):
        issues.append(Issue(day, Severity.ERROR, IssueCode.NO_FUTURES, "-", "no futures rows"))
    if not options:
        issues.append(Issue(day, Severity.ERROR, IssueCode.NO_OPTIONS, "-", "no option rows"))
        return issues
    near = [bar for bar in options if (bar.expiry - day).days <= MAX_DAYS_FOR_PAIR_CHECK]
    issues += _missing_pairs(day, near)
    nearest = min(bar.expiry for bar in options)
    if nearest - day > timedelta(days=MAX_DAYS_TO_NEAREST_WEEKLY_EXPIRY):
        detail = f"nearest expiry {nearest}"
        issues.append(Issue(day, Severity.WARNING, IssueCode.NO_NEAR_WEEKLY_EXPIRY, "-", detail))
    return issues


def _missing_pairs(day: date, options: Iterable[DailyContractBar]) -> list[Issue]:
    sides: dict[tuple[date, Decimal | None], set[OptionType | None]] = {}
    for bar in options:
        sides.setdefault((bar.expiry, bar.strike), set()).add(bar.option_type)
    both = {OptionType.CALL, OptionType.PUT}
    return [
        Issue(
            day,
            Severity.WARNING,
            IssueCode.MISSING_CALL_OR_PUT,
            f"{expiry} {strike}",
            f"only {sorted(str(t) for t in present)}",
        )
        for (expiry, strike), present in sorted(sides.items(), key=lambda item: str(item[0]))
        if present != both
    ]

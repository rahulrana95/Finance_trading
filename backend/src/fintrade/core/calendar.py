"""Trading days, expiries, and the entry / exit timing rules from AGENTS.md section 1.

Built from observed data (days with an exchange file are trading days; listed option
expiries are expiries), so holidays and shifted expiries are handled without a
hand-maintained list.
"""

from bisect import bisect_left, bisect_right
from collections.abc import Iterable
from datetime import date, datetime, timedelta

from fintrade.core.errors import DataError, InvalidInputError
from fintrade.core.limits import HARD_LIMITS
from fintrade.core.timezone import IST

DAYS_PER_WEEK = 7
# "Next week's expiry only": at least the minimum days away, and within the following week.
MAX_DAYS_TO_EXPIRY_AT_ENTRY = HARD_LIMITS.min_days_to_expiry_at_entry + DAYS_PER_WEEK


class TradingCalendar:
    def __init__(self, trading_days: Iterable[date]) -> None:
        self._days = sorted(set(trading_days))
        if not self._days:
            raise InvalidInputError("trading calendar needs at least one trading day")
        self._set = frozenset(self._days)

    @property
    def first_day(self) -> date:
        return self._days[0]

    @property
    def last_day(self) -> date:
        return self._days[-1]

    def is_trading_day(self, day: date) -> bool:
        self._check_covered(day)
        return day in self._set

    def previous_trading_day(self, day: date) -> date:
        """Latest trading day strictly before `day`."""
        self._check_covered(day)
        index = bisect_left(self._days, day) - 1
        if index < 0:
            raise DataError(f"no trading day before {day} in calendar")
        return self._days[index]

    def next_trading_day(self, day: date) -> date:
        """Earliest trading day strictly after `day`."""
        self._check_covered(day)
        index = bisect_right(self._days, day)
        if index >= len(self._days):
            raise DataError(f"no trading day after {day} in calendar")
        return self._days[index]

    def trading_days_between(self, start: date, end: date) -> int:
        """Trading days in the half-open range (start, end]."""
        if start > end:
            raise InvalidInputError(f"start {start} is after end {end}")
        self._check_covered(start)
        self._check_covered(end)
        return bisect_right(self._days, end) - bisect_right(self._days, start)

    def _check_covered(self, day: date) -> None:
        if not self.first_day <= day <= self.last_day:
            raise DataError(f"{day} is outside calendar {self.first_day}..{self.last_day}")


class ExpiryCalendar:
    def __init__(self, expiries: Iterable[date], trading: TradingCalendar) -> None:
        self._expiries = sorted(set(expiries))
        self._trading = trading

    def entry_expiry(self, today: date) -> date | None:
        """Expiry for a new entry today: the nearest one at least the minimum days away,
        if it falls within the following week. None means no valid entry expiry today.
        """
        index = bisect_left(
            self._expiries, today + timedelta(HARD_LIMITS.min_days_to_expiry_at_entry)
        )
        if index >= len(self._expiries):
            return None
        expiry = self._expiries[index]
        return expiry if (expiry - today).days <= MAX_DAYS_TO_EXPIRY_AT_ENTRY else None

    def exit_deadline(self, expiry: date) -> datetime:
        """Positions must be closed by this moment: cutoff time on the trading day before
        expiry (AGENTS.md: never hold into expiry day)."""
        if expiry not in self._expiries:
            raise InvalidInputError(f"{expiry} is not a known expiry")
        day_before = self._trading.previous_trading_day(expiry)
        return datetime.combine(day_before, HARD_LIMITS.exit_cutoff_day_before_expiry, tzinfo=IST)

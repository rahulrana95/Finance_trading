"""Real Oct-Nov 2026 NSE calendar, as observed in the bhavcopy data."""

from datetime import date

from fintrade.core.calendar import ExpiryCalendar, TradingCalendar
from fintrade.core.dates import weekdays

HOLIDAYS = frozenset({date(2026, 10, 2), date(2026, 10, 20), date(2026, 11, 10)})
# Weekly expiries are Tuesdays; 2026-10-19 and 2026-11-09 moved to Monday for holidays.
EXPIRIES = (
    date(2026, 10, 6), date(2026, 10, 13), date(2026, 10, 19), date(2026, 10, 27),
    date(2026, 11, 3), date(2026, 11, 9), date(2026, 11, 17), date(2026, 11, 24),
)  # fmt: skip


def trading_calendar() -> TradingCalendar:
    days = weekdays(date(2026, 10, 1), date(2026, 11, 30))
    return TradingCalendar(day for day in days if day not in HOLIDAYS)


def expiry_calendar() -> ExpiryCalendar:
    return ExpiryCalendar(EXPIRIES, trading_calendar())

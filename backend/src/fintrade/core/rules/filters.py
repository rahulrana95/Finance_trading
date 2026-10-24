"""Entry filters from RULES.md section 3 (tunable, unlike the hard limits in entry.py)."""

from collections.abc import Mapping, Set
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from fintrade.core.calendar import TradingCalendar
from fintrade.core.errors import RuleViolation
from fintrade.core.instruments import CreditSpread, OptionContract, Position
from fintrade.core.money import Rupees
from fintrade.core.pnl import credit_points
from fintrade.core.rules.strategy_config import DEFAULT_ENTRY_FILTERS, EntryFilterConfig
from fintrade.core.timezone import ensure_ist

_PCT = Decimal(100)


class FilterRule(StrEnum):
    OUTSIDE_ENTRY_WINDOW = "outside_entry_window"
    CREDIT_TOO_LOW = "credit_too_low"
    EVENT_BLACKOUT = "event_blackout"
    VIX_OUT_OF_BAND = "vix_out_of_band"
    VIX_MISSING = "vix_missing"


@dataclass(frozen=True, slots=True)
class FilterInputs:
    position: Position
    entry_prices: Mapping[OptionContract, Rupees]
    now: datetime
    india_vix: Decimal | None
    event_days: Set[date]
    calendar: TradingCalendar


def check_filters(
    inputs: FilterInputs, config: EntryFilterConfig = DEFAULT_ENTRY_FILTERS
) -> list[RuleViolation]:
    return [
        *_entry_window(inputs, config),
        *_min_credit(inputs, config),
        *_events(inputs, config),
        *_vix(inputs, config),
    ]


def _entry_window(inputs: FilterInputs, config: EntryFilterConfig) -> list[RuleViolation]:
    clock = ensure_ist(inputs.now).time()
    if config.entry_window_start <= clock < config.entry_window_end:
        return []
    window = f"[{config.entry_window_start}, {config.entry_window_end})"
    return [RuleViolation(FilterRule.OUTSIDE_ENTRY_WINDOW, f"{clock} not in {window}")]


def _sides(position: Position) -> tuple[CreditSpread, ...]:
    if isinstance(position, CreditSpread):
        return (position,)
    return (position.put_spread, position.call_spread)


def _min_credit(inputs: FilterInputs, config: EntryFilterConfig) -> list[RuleViolation]:
    found: list[RuleViolation] = []
    for side in _sides(inputs.position):
        credit = credit_points(side, inputs.entry_prices)
        needed = side.width * config.min_credit_pct_of_width / _PCT
        if credit < needed:
            pct = config.min_credit_pct_of_width
            detail = f"{side.structure} credit {credit} < {needed} ({pct}% of {side.width})"
            found.append(RuleViolation(FilterRule.CREDIT_TOO_LOW, detail))
    return found


def _events(inputs: FilterInputs, config: EntryFilterConfig) -> list[RuleViolation]:
    if not config.event_blackout:
        return []
    today = ensure_ist(inputs.now).date()
    next_day = inputs.calendar.next_trading_day(today)
    hits = sorted(day for day in inputs.event_days if today <= day <= next_day)
    if hits:
        return [RuleViolation(FilterRule.EVENT_BLACKOUT, f"event on {hits[0]}")]
    return []


def _vix(inputs: FilterInputs, config: EntryFilterConfig) -> list[RuleViolation]:
    if config.vix_min is None and config.vix_max is None:
        return []
    vix = inputs.india_vix
    if vix is None or not vix.is_finite():
        return [RuleViolation(FilterRule.VIX_MISSING, "India VIX needed for the VIX band")]
    too_low = config.vix_min is not None and vix < config.vix_min
    too_high = config.vix_max is not None and vix > config.vix_max
    if too_low or too_high:
        band = f"[{config.vix_min}, {config.vix_max}]"
        return [RuleViolation(FilterRule.VIX_OUT_OF_BAND, f"VIX {vix} outside {band}")]
    return []

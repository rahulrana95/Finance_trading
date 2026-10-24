"""Per-expiry contract specs (lot size, trading window) derived from the data itself.

The lot size reported is the one that applies on the expiry's LAST observed trading day,
because NSE revises lot sizes and long-dated contracts carry positions from before a
revision (e.g. 75-unit and 65-unit positions mixed give an open-interest gcd of 5).

Lot size source, per expiry:
- STATED: the exchange file states it (UDiFF format, 2024-07 onwards); the value on the
  last observed day is used.
- INFERRED: greatest common divisor of open interest and its daily change over the
  `LOT_WINDOW_DAYS` ending on the last observed day. Open interest is in units and is a
  whole number of lots, so the gcd over many values is the lot size.
- The window gcd is always recorded as `oi_gcd`. Open interest counts ALL open positions,
  so for long-dated contracts it still mixes pre-revision lots; a stated size therefore
  wins, and a disagreement is flagged (`oi_gcd_consistent`) rather than fatal.
- UNKNOWN: nothing stated and the gcd is not trustworthy: data does not reach within
  `LOT_WINDOW_DAYS` of expiry, or fewer than `MIN_OBSERVATIONS_FOR_INFERENCE` values
  (e.g. a newly listed weekly with no open interest yet). Lot size is None; anything
  that trades must refuse it (fail closed).
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from math import gcd

from fintrade.core.bars import ContractKind, DailyContractBar
from fintrade.core.errors import DataError

LOT_WINDOW_DAYS = 14
# Fewer values than this, or data that stops well before expiry, can give a gcd that is a
# multiple of the real lot (real case: 20 values gave 150 instead of 75), so: UNKNOWN.
MIN_OBSERVATIONS_FOR_INFERENCE = 100


class LotSizeSource(StrEnum):
    STATED = "stated"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExpirySpec:
    expiry: date
    lot_size: int | None  # None only when source is UNKNOWN
    source: LotSizeSource
    first_traded: date
    last_traded: date
    observations: int  # non-zero OI values in the window behind the gcd
    oi_gcd: int | None

    @property
    def oi_gcd_consistent(self) -> bool | None:
        """Does the window gcd agree with the lot size? None when nothing to compare."""
        if self.oi_gcd is None or self.lot_size is None:
            return None
        return self.oi_gcd % self.lot_size == 0


@dataclass
class _Days:
    units: dict[date, list[int]]
    stated: dict[date, set[int]]


def infer_lot_size(values: Iterable[int]) -> int | None:
    """gcd of the non-zero values, or None if there are none."""
    result = 0
    for value in values:
        result = gcd(result, abs(value))
    return result or None


def derive_expiry_specs(bars: Iterable[DailyContractBar]) -> list[ExpirySpec]:
    """One spec per option expiry seen in `bars`, sorted by expiry."""
    by_expiry: dict[date, _Days] = defaultdict(lambda: _Days(defaultdict(list), defaultdict(set)))
    for bar in bars:
        if bar.kind is not ContractKind.OPTION:
            continue
        days = by_expiry[bar.expiry]
        days.units[bar.trade_date] += [bar.open_interest, bar.change_in_oi]
        if bar.lot_size is not None:
            days.stated[bar.trade_date].add(bar.lot_size)
    return [_spec(expiry, by_expiry[expiry]) for expiry in sorted(by_expiry)]


def _spec(expiry: date, days: _Days) -> ExpirySpec:
    first, last = min(days.units), max(days.units)
    window_start = last - timedelta(days=LOT_WINDOW_DAYS - 1)
    window = [v for day, values in days.units.items() if day >= window_start for v in values]
    inferred = infer_lot_size(window)
    observations = sum(1 for value in window if value)
    stated = _latest_stated(expiry, days.stated)
    lot_size: int | None
    if stated is not None:
        lot_size, source = stated, LotSizeSource.STATED
    elif inferred is not None and _trustworthy(expiry, last, observations):
        lot_size, source = inferred, LotSizeSource.INFERRED
    else:
        lot_size, source = None, LotSizeSource.UNKNOWN
    return ExpirySpec(expiry, lot_size, source, first, last, observations, inferred)


def _trustworthy(expiry: date, last_traded: date, observations: int) -> bool:
    reaches_expiry = (expiry - last_traded).days < LOT_WINDOW_DAYS
    return reaches_expiry and observations >= MIN_OBSERVATIONS_FOR_INFERENCE


def _latest_stated(expiry: date, stated: dict[date, set[int]]) -> int | None:
    if not stated:
        return None
    last_day = max(stated)
    sizes = stated[last_day]
    if len(sizes) > 1:
        raise DataError(
            f"expiry {expiry}: conflicting stated lot sizes {sorted(sizes)} on {last_day}"
        )
    (size,) = sizes
    return size

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
- CONSENSUS: `resolve_with_neighbours` replaced an INFERRED / UNKNOWN value. Long-dated
  monthly contracts (listed years ahead) carry positions from much older lot sizes, so
  their gcd can be a divisor of the real lot (real case: 25 instead of 75 or 50). New
  trades in any expiry use the market lot, which nearby expiries show.
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
from enum import StrEnum
from math import gcd

from fintrade.core.bars import ContractKind, DailyContractBar
from fintrade.core.errors import DataError

LOT_WINDOW_DAYS = 14
NEIGHBOUR_WINDOW_DAYS = 7  # expiries this close share the market lot for new trades
RELABEL_WINDOW_DAYS = 7  # a holiday moves an expiry by days, never by more than a week
# Only reliable specs vote: short-lived contracts with plenty of data (long-dated ones
# carry stale positions; real case 2023-06-28/29 voted for each other with gcd 25).
MAX_VOTER_LIFE_DAYS = 120  # weeklies ~60-70 days, monthlies ~90; long-dated >= ~1 year
MIN_VOTER_OBSERVATIONS = 1000
# Fewer values than this, or data that stops well before expiry, can give a gcd that is a
# multiple of the real lot (real case: 20 values gave 150 instead of 75), so: UNKNOWN.
MIN_OBSERVATIONS_FOR_INFERENCE = 100


class LotSizeSource(StrEnum):
    STATED = "stated"
    INFERRED = "inferred"
    CONSENSUS = "consensus"
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

    @property
    def expired_as_listed(self) -> bool:
        """Traded on its own expiry day. False for a holiday-moved expiry date (e.g.
        2023-06-29 moved to 2023-06-28) or one still in the future."""
        return self.last_traded == self.expiry

    @property
    def is_reliable_voter(self) -> bool:
        if self.lot_size is None:
            return False
        if self.source is LotSizeSource.STATED:
            return True
        life = (self.expiry - self.first_traded).days
        return (
            self.source is LotSizeSource.INFERRED
            and life <= MAX_VOTER_LIFE_DAYS
            and self.observations >= MIN_VOTER_OBSERVATIONS
        )


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


def resolve_with_neighbours(specs: list[ExpirySpec]) -> list[ExpirySpec]:
    """Fix INFERRED / UNKNOWN lot sizes that disagree with expiries within
    `NEIGHBOUR_WINDOW_DAYS`. A value is replaced only when the neighbours agree on one
    lot size and the value is UNKNOWN or divides it (the signature of stale positions
    pulling the gcd down). STATED values are never changed."""
    return [_resolved(spec, specs) for spec in specs]


def _resolved(spec: ExpirySpec, specs: list[ExpirySpec]) -> ExpirySpec:
    if spec.source not in {LotSizeSource.INFERRED, LotSizeSource.UNKNOWN}:
        return spec
    window = timedelta(days=NEIGHBOUR_WINDOW_DAYS)
    neighbour_lots = {
        other.lot_size
        for other in specs
        if other is not spec
        and other.lot_size is not None  # implied by is_reliable_voter; stated for typing
        and other.is_reliable_voter
        and abs(other.expiry - spec.expiry) <= window
    }
    if len(neighbour_lots) != 1:
        return spec
    (market_lot,) = neighbour_lots
    if spec.lot_size == market_lot:
        return spec
    if spec.lot_size is not None and market_lot % spec.lot_size != 0:
        return spec
    return replace(spec, lot_size=market_lot, source=LotSizeSource.CONSENSUS)


def expiry_relabels(specs: Sequence[ExpirySpec]) -> dict[date, date]:
    """Listed expiry -> the date its contracts actually expired, for holiday moves where NSE
    re-labelled live contracts with the new date (2023-06-29 became 2023-06-28: the same
    contracts carry expiry 06-29 up to 06-27 and 06-28 on 06-28).

    Seen in the data as an expiry that trades only on its own expiry day, plus a listed
    expiry up to `RELABEL_WINDOW_DAYS` later whose trading stopped in the week before.
    """
    window = timedelta(RELABEL_WINDOW_DAYS)
    relabels: dict[date, date] = {}
    for moved in specs:
        if not moved.first_traded == moved.last_traded == moved.expiry:
            continue
        sources = [
            listed.expiry
            for listed in specs
            if moved.expiry < listed.expiry <= moved.expiry + window
            and moved.expiry - window <= listed.last_traded < moved.expiry
        ]
        if len(sources) > 1:
            raise DataError(f"{moved.expiry} could be the moved date of several: {sources}")
        if sources:
            relabels[sources[0]] = moved.expiry
    return relabels

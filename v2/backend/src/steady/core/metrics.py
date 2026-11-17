"""Recovery and risk figures from a series of daily closes. Pure functions, no I/O."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from steady.constants import (
    FALL_PCT,
    MIN_HISTORY_DAYS,
    RECOVERY_WITHIN_DAYS,
    REFERENCE_WINDOW_DAYS,
)

DAYS_PER_YEAR = 365.25


@dataclass(frozen=True)
class FallEvent:
    """One fall of at least the threshold below the recent high."""

    start: int
    depth_pct: float
    recovery_days: int | None
    open_days: int


@dataclass(frozen=True)
class RecoveryStats:
    count: int
    recovered_within_pct: float | None
    longest_days: int
    open_days: int


def validate_closes(closes: Sequence[float]) -> None:
    if any(not math.isfinite(c) or c <= 0 for c in closes):
        raise ValueError("Prices must be positive, finite numbers")


def _high_at(closes: Sequence[float], index: int, window: int) -> float:
    return max(closes[max(0, index - window + 1) : index + 1])


def reference_high(
    closes: Sequence[float],
    window: int = REFERENCE_WINDOW_DAYS,
    min_history: int = MIN_HISTORY_DAYS,
) -> float | None:
    """Highest close of the last `window` days, or None without enough history."""
    if len(closes) < min_history:
        return None
    return _high_at(closes, len(closes) - 1, window)


def below_high_pct(price: float, high: float) -> float:
    return 0.0 if price >= high else (1 - price / high) * 100


def fall_events(
    closes: Sequence[float],
    pct: float = FALL_PCT,
    window: int = REFERENCE_WINDOW_DAYS,
    min_history: int = MIN_HISTORY_DAYS,
    start_index: int = 0,
) -> list[FallEvent]:
    """Each time the close first sits `pct` below its recent high, until it is back there."""
    events: list[FallEvent] = []
    last = len(closes) - 1
    t = max(start_index, min_history)
    while t <= last:
        high = _high_at(closes, t, window)
        if closes[t] > high * (1 - pct / 100):
            t += 1
            continue
        recovered = next((u for u in range(t + 1, last + 1) if closes[u] >= high), None)
        end = last if recovered is None else recovered
        events.append(
            FallEvent(
                start=t,
                depth_pct=(1 - min(closes[t : end + 1]) / high) * 100,
                recovery_days=None if recovered is None else recovered - t,
                open_days=last - t if recovered is None else 0,
            )
        )
        t = end + 1
    return events


def recovery_stats(
    events: Sequence[FallEvent], within_days: int = RECOVERY_WITHIN_DAYS
) -> RecoveryStats:
    if not events:
        return RecoveryStats(count=0, recovered_within_pct=None, longest_days=0, open_days=0)
    quick = sum(1 for e in events if e.recovery_days is not None and e.recovery_days <= within_days)
    return RecoveryStats(
        count=len(events),
        recovered_within_pct=100 * quick / len(events),
        longest_days=max(e.recovery_days or e.open_days for e in events),
        open_days=max(e.open_days for e in events),
    )


def max_drawdown_pct(closes: Sequence[float]) -> float:
    """Deepest fall from any earlier peak, as a positive percentage."""
    peak = 0.0
    worst = 0.0
    for close in closes:
        peak = max(peak, close)
        worst = max(worst, (1 - close / peak) * 100)
    return worst


def history_years(dates: Sequence[date]) -> float:
    return (dates[-1] - dates[0]).days / DAYS_PER_YEAR if dates else 0.0

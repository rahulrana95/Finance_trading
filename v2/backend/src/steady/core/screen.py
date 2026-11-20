"""Deep falls from the 1-year high and what followed them. Pure functions, no I/O."""

from collections import deque
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import pairwise

from steady.constants import (
    FURTHER_FALL_PCT,
    GAIN_6M_PCT,
    GAIN_12M_PCT,
    HALF_YEAR_DAYS,
    SCREEN_LEVELS_PCT,
    SCREEN_MIN_HISTORY,
    SCREEN_REARM_PCT,
    SCREEN_WINDOW_DAYS,
    YEAR_DAYS,
)


@dataclass(frozen=True)
class DipEvent:
    """The first close at least `level` % below the 1-year high, and what came next."""

    index: int
    level: float
    market_down: bool
    best_6m: float
    end_6m: float
    best_12m: float | None
    end_12m: float | None
    worst_12m: float | None


@dataclass(frozen=True)
class Odds:
    """How falls of one size turned out, with or without a market-wide fall."""

    level: float
    market_down: bool
    events: int
    gain10_6m_pct: float
    gain20_6m_pct: float
    higher_6m_pct: float
    events_12m: int
    gain30_12m_pct: float
    higher_12m_pct: float
    fell_further_12m_pct: float


def below_high_series(
    closes: Sequence[float], window: int = SCREEN_WINDOW_DAYS, min_history: int = SCREEN_MIN_HISTORY
) -> list[float | None]:
    """For each day, % below the highest close of the last `window` days (None too early)."""
    out: list[float | None] = []
    highs: deque[int] = deque()  # indexes of closes, largest first
    for t, close in enumerate(closes):
        while highs and closes[highs[-1]] <= close:
            highs.pop()
        highs.append(t)
        if highs[0] <= t - window:
            highs.popleft()
        out.append(None if t + 1 < min_history else (1 - close / closes[highs[0]]) * 100)
    return out


def level_reached(below_pct: float, levels: Sequence[float] = SCREEN_LEVELS_PCT) -> float:
    """The deepest level this fall has reached, or 0 when it has reached none."""
    return max((level for level in levels if below_pct >= level), default=0.0)


def _change(closes: Sequence[float], start: int, picked: float) -> float:
    return (picked / closes[start] - 1) * 100


def dip_events(
    closes: Sequence[float],
    market_down: Sequence[bool],
    levels: Sequence[float] = SCREEN_LEVELS_PCT,
) -> list[DipEvent]:
    """Every fall that has at least six months of prices after it."""
    depths = below_high_series(closes)
    events: list[DipEvent] = []
    armed = dict.fromkeys(levels, True)
    last = dict.fromkeys(levels, -YEAR_DAYS - 1)
    for t, depth in enumerate(depths):
        if depth is None:
            continue
        for level in levels:
            if depth <= SCREEN_REARM_PCT or t - last[level] > YEAR_DAYS:
                armed[level] = True
            if not armed[level] or depth < level:
                continue
            armed[level], last[level] = False, t
            if t + HALF_YEAR_DAYS >= len(closes):
                continue
            half = closes[t + 1 : t + HALF_YEAR_DAYS + 1]
            year = closes[t + 1 : t + YEAR_DAYS + 1] if t + YEAR_DAYS < len(closes) else None
            events.append(
                DipEvent(
                    index=t,
                    level=level,
                    market_down=market_down[t],
                    best_6m=_change(closes, t, max(half)),
                    end_6m=_change(closes, t, half[-1]),
                    best_12m=_change(closes, t, max(year)) if year else None,
                    end_12m=_change(closes, t, year[-1]) if year else None,
                    worst_12m=_change(closes, t, min(year)) if year else None,
                )
            )
    return events


def _share(flags: Sequence[bool]) -> float:
    return round(100 * sum(flags) / len(flags), 1) if flags else 0.0


def odds_table(
    events: Iterable[DipEvent], levels: Sequence[float] = SCREEN_LEVELS_PCT
) -> list[Odds]:
    """One row per fall size and market state, from every stock's past falls."""
    events = list(events)
    table = []
    for level in levels:
        for down in (True, False):
            group = [e for e in events if e.level == level and e.market_down == down]
            # These three fields are set together, so one check covers them all.
            year = [
                (e.best_12m, e.end_12m, e.worst_12m)
                for e in group
                if e.best_12m is not None and e.end_12m is not None and e.worst_12m is not None
            ]
            table.append(
                Odds(
                    level=level,
                    market_down=down,
                    events=len(group),
                    gain10_6m_pct=_share([e.best_6m >= GAIN_6M_PCT[0] for e in group]),
                    gain20_6m_pct=_share([e.best_6m >= GAIN_6M_PCT[1] for e in group]),
                    higher_6m_pct=_share([e.end_6m > 0 for e in group]),
                    events_12m=len(year),
                    gain30_12m_pct=_share([best >= GAIN_12M_PCT for best, _, _ in year]),
                    higher_12m_pct=_share([end > 0 for _, end, _ in year]),
                    fell_further_12m_pct=_share(
                        [worst <= -FURTHER_FALL_PCT for _, _, worst in year]
                    ),
                )
            )
    return table


def worst_day_pct(closes: Sequence[float], window: int = SCREEN_WINDOW_DAYS) -> float:
    """The biggest one-day fall in the last `window` days, as a positive %."""
    recent = closes[-window - 1 :]
    return max([(1 - b / a) * 100 for a, b in pairwise(recent)] + [0.0])

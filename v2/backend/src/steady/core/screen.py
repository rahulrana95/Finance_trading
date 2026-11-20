"""Deep falls from the 1-year high and what followed them. Pure functions, no I/O."""

from collections import deque
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import pairwise

from steady.constants import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    DEMERGER_DROP_PCT,
    FURTHER_FALL_PCT,
    GAIN_6M_PCT,
    GAIN_12M_PCT,
    HALF_YEAR_DAYS,
    HIGH_MIN_LEVEL_PCT,
    MARKET_DEEP,
    MARKET_DEEP_PCT,
    MARKET_DOWN,
    MARKET_DOWN_PCT,
    MARKET_FINE,
    MARKET_STATES,
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
    market: str
    best_6m: float
    end_6m: float
    best_12m: float | None
    end_12m: float | None
    worst_12m: float | None


@dataclass(frozen=True)
class Odds:
    """How falls of one size turned out in one market state (deep fall, fall, or fine)."""

    level: float
    market: str
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
    market: Sequence[str],
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
                    market=market[t],
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
        for state in MARKET_STATES:
            group = [e for e in events if e.level == level and e.market == state]
            # These three fields are set together, so one check covers them all.
            year = [
                (e.best_12m, e.end_12m, e.worst_12m)
                for e in group
                if e.best_12m is not None and e.end_12m is not None and e.worst_12m is not None
            ]
            table.append(
                Odds(
                    level=level,
                    market=state,
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


def market_state(below_pct: float) -> str:
    """How far the index is below its 1-year high, as one of three states."""
    if below_pct >= MARKET_DEEP_PCT:
        return MARKET_DEEP
    return MARKET_DOWN if below_pct >= MARKET_DOWN_PCT else MARKET_FINE


def confidence(level: float, market: str, worst_day: float) -> str:
    """High only for the case with the best tested record: a deep market fall and a 25%+ fall.

    Measured on 2015-2020 and 2021-2026 separately (BACKTEST_RESULTS.md, 2026-11-20): the
    stock's own past recoveries, size and long-term trend did not change the odds, so they
    are not part of this.
    """
    if market == MARKET_FINE or worst_day >= DEMERGER_DROP_PCT:
        return CONFIDENCE_LOW
    if market == MARKET_DEEP and level >= HIGH_MIN_LEVEL_PCT:
        return CONFIDENCE_HIGH
    return CONFIDENCE_MEDIUM

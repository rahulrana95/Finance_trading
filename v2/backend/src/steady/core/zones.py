"""Buy zones below the reference high."""

from collections.abc import Sequence

from steady.constants import BUY_LEVELS_PCT


def zone(below_pct: float, levels: Sequence[float] = BUY_LEVELS_PCT) -> int:
    """0 when not in a buy zone, otherwise the deepest level reached (1-based)."""
    return sum(1 for level in levels if below_pct >= level)


def level_price(reference_high: float, pct: float) -> float:
    return round(reference_high * (1 - pct / 100), 2)

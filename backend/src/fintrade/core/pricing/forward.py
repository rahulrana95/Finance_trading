"""Forward price from put-call parity: F = K + (C - P) * e^(rT).

Using the market's own forward avoids guessing dividends and the futures basis. The
median over the strikes nearest the money makes one bad quote harmless.
"""

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from fintrade.core.errors import DataError, InvalidInputError

STRIKES_FOR_FORWARD = 5


@dataclass(frozen=True, slots=True)
class StrikeQuote:
    strike: float
    call: float
    put: float


def forward_from_chain(quotes: Sequence[StrikeQuote], years: float, rate: float) -> float:
    """Median parity forward over the `STRIKES_FOR_FORWARD` strikes with the smallest
    |call - put| (the ones nearest the money, where both prices are most reliable)."""
    if years <= 0 or not math.isfinite(years) or not math.isfinite(rate):
        raise InvalidInputError(f"invalid years / rate: {years}, {rate}")
    usable = [q for q in quotes if q.strike > 0 and q.call > 0 and q.put > 0]
    if not usable:
        raise DataError("no strike with both a call and a put price to derive the forward")
    nearest = sorted(usable, key=lambda q: abs(q.call - q.put))[:STRIKES_FOR_FORWARD]
    growth = math.exp(rate * years)
    return statistics.median(q.strike + (q.call - q.put) * growth for q in nearest)

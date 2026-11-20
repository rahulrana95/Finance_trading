"""The reasons behind a stock's confidence, in plain words. Pure."""

from steady.constants import (
    DEMERGER_DROP_PCT,
    HIGH_MIN_LEVEL_PCT,
    MARKET_DEEP,
    MARKET_DEEP_PCT,
    MARKET_DOWN_PCT,
    MARKET_FINE,
)
from steady.core.screen import Odds
from steady.domain import Evidence, ScreenRow
from steady.utils.format import inr

EVIDENCE_GOOD_PCT = 70.0  # the past result counts in favour when this share ended higher


def build_evidence(
    row: ScreenRow, market: str, market_below: float, odds: Odds | None
) -> tuple[Evidence, ...]:
    past = (
        f"{odds.events} past falls like this: {odds.higher_6m_pct:.0f}% were higher after "
        f"6 months, {odds.higher_12m_pct:.0f}% after a year, and "
        f"{odds.fell_further_12m_pct:.0f}% fell another 20% first."
        if odds and odds.events
        else "No past fall like this to compare with."
    )
    return (
        Evidence(
            "The whole market is in a fall",
            market != MARKET_FINE,
            f"Nifty is {market_below:.1f}% below its 1-year high; a market-wide fall "
            f"starts at {MARKET_DOWN_PCT:.0f}%.",
        ),
        Evidence(
            f"The market fall is deep ({MARKET_DEEP_PCT:.0f}% or more)",
            market == MARKET_DEEP,
            "This is the case with the best record in both test periods.",
        ),
        Evidence(
            f"The stock has fallen {HIGH_MIN_LEVEL_PCT:.0f}% or more",
            row.level >= HIGH_MIN_LEVEL_PCT,
            f"It is {row.below_pct:.1f}% below its 1-year high of {inr(row.year_high)}.",
        ),
        Evidence(
            "No sign of a demerger or split",
            row.worst_day_pct < DEMERGER_DROP_PCT,
            f"Its biggest one-day drop in the last year was {row.worst_day_pct:.0f}%.",
        ),
        Evidence(
            "Similar falls usually ended higher",
            bool(odds and odds.events and odds.higher_6m_pct >= EVIDENCE_GOOD_PCT),
            past,
        ),
    )

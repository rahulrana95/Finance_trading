"""Screens the whole stock list for deep falls and the odds that followed similar ones."""

import logging
import threading
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, timedelta

from steady.clock import Clock
from steady.constants import (
    MARKET_DOWN_PCT,
    MARKET_SYMBOL,
    SCREEN_LEVELS_PCT,
    SCREEN_MAX_AGE_HOURS,
    SCREEN_WORKERS,
)
from steady.core.screen import (
    DipEvent,
    below_high_series,
    dip_events,
    level_reached,
    odds_table,
    worst_day_pct,
)
from steady.domain import Close, Listing, Screen, ScreenRow
from steady.ports import PriceSource, PriceSourceError, Store

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScreenState:
    running: bool
    error: str | None
    screen: Screen | None


def _new_id() -> str:
    return uuid.uuid4().hex


def check_stock(
    listing: Listing, closes: list[Close], market_below: dict[date, float]
) -> tuple[list[DipEvent], ScreenRow | None]:
    """A stock's past falls, and its row if it is in a deep fall today."""
    prices = [c.close for c in closes]
    down = [market_below.get(c.day, 0.0) >= MARKET_DOWN_PCT for c in closes]
    events = dip_events(prices, down)
    below = below_high_series(prices)[-1]
    level = level_reached(below) if below is not None else 0.0
    if level == 0.0 or below is None:
        return events, None
    own = [e for e in events if e.level == SCREEN_LEVELS_PCT[0]]
    with_year = [e for e in own if e.end_12m is not None]
    row = ScreenRow(
        symbol=listing.symbol,
        name=listing.name,
        industry=listing.industry,
        last_price=round(prices[-1], 2),
        price_as_of=closes[-1].day.isoformat(),
        year_high=round(prices[-1] / (1 - below / 100), 2),
        below_pct=round(below, 1),
        level=level,
        own_falls=len(own),
        own_higher_after_year=sum(1 for e in with_year if e.end_12m is not None and e.end_12m > 0),
        own_falls_with_year=len(with_year),
        worst_day_pct=round(worst_day_pct(prices), 1),
    )
    return events, row


class ScreenerService:
    def __init__(
        self,
        universe: list[Listing],
        prices: PriceSource,
        store: Store,
        clock: Clock,
        new_id: Callable[[], str] = _new_id,
    ) -> None:
        self._universe = universe
        self._prices = prices
        self._store = store
        self._clock = clock
        self._new_id = new_id
        self._lock = threading.Lock()
        self._running = False
        self._error: str | None = None

    def state(self) -> ScreenState:
        return ScreenState(self._running, self._error, self._store.latest_screen())

    def start(self) -> bool:
        """Marks a screen as running. False when one already is."""
        with self._lock:
            if self._running:
                return False
            self._running, self._error = True, None
            return True

    def execute(self) -> None:
        try:
            self._store.save_screen(self._screen())
        except Exception as error:  # the service must outlive a failed screen
            log.exception("screen failed")
            self._error = (
                str(error) if isinstance(error, PriceSourceError) else "The screen failed."
            )
        finally:
            self._running = False

    def run(self) -> ScreenState:
        if self.start():
            self.execute()
        return self.state()

    def run_if_stale(self) -> bool:
        """Runs unless a recent screen is already stored (so a restart does not refetch)."""
        latest = self._store.latest_screen()
        fresh = self._clock() - timedelta(hours=SCREEN_MAX_AGE_HOURS)
        if latest is not None and latest.created_at >= fresh:
            return False
        self.run()
        return True

    def _closes(self, listing: Listing) -> list[Close] | None:
        try:
            return self._prices.daily_closes(listing.symbol)
        except PriceSourceError:
            return None

    def _screen(self) -> Screen:
        market = self._prices.daily_closes(MARKET_SYMBOL)
        depths = below_high_series([c.close for c in market])
        market_below = {c.day: d for c, d in zip(market, depths, strict=True) if d is not None}
        market_now = depths[-1] or 0.0
        events: list[DipEvent] = []
        rows: list[ScreenRow] = []
        priced = 0
        with ThreadPoolExecutor(max_workers=SCREEN_WORKERS) as pool:
            for listing, closes in zip(
                self._universe, pool.map(self._closes, self._universe), strict=True
            ):
                if not closes:
                    continue
                priced += 1
                found, row = check_stock(listing, closes, market_below)
                events += found
                if row:
                    rows.append(row)
        if not priced:
            raise PriceSourceError("The price source did not answer for any stock.")
        rows.sort(key=lambda r: (-r.level, -r.below_pct, r.symbol))
        return Screen(
            id=self._new_id(),
            created_at=self._clock(),
            universe=len(self._universe),
            priced=priced,
            market_below_pct=round(market_now, 1),
            market_down=market_now >= MARKET_DOWN_PCT,
            odds=tuple(odds_table(events)),
            rows=tuple(rows),
        )

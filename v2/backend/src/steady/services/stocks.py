"""Builds the stock table: prices from the price source, scores from the core rules."""

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime

from steady.clock import Clock
from steady.constants import (
    HISTORY_SAMPLE_DAYS,
    HISTORY_SAMPLE_STEP,
    HISTORY_YEARS_RANGE,
    MAX_FETCH_WORKERS,
    METRICS_START,
    NEED_FRESH_PRICES,
    NEED_LOT_SIZE,
    NEED_OFFICIAL_PRICES,
    NEED_PRICE_HISTORY,
    PRICE_TTL_SECONDS,
    STALE_AFTER_DAYS,
)
from steady.core.metrics import (
    below_high_pct,
    fall_events,
    history_years,
    max_drawdown_pct,
    recovery_stats,
    reference_high,
    validate_closes,
)
from steady.core.scoring import (
    FinancialInput,
    StabilityInput,
    evidence,
    financial_score,
    stability_score,
)
from steady.core.zones import zone
from steady.domain import Close, StockSeed
from steady.ports import PriceSource, PriceSourceError


class StockNotFoundError(Exception):
    """No stock with that symbol is on the list."""


@dataclass(frozen=True)
class StockView:
    """One row of the stock table. Price fields are zero when prices are unavailable."""

    seed: StockSeed
    last_price: float
    price_as_of: str
    reference_high: float
    below_high_pct: float
    zone: int
    falls10: int
    recovered12m_pct: float
    longest_recovery_days: int
    max_drawdown_pct: float
    history_years: float
    stability: int
    financial: int
    data_quality: int
    evidence: int
    needs: tuple[str, ...]
    history: tuple[float, ...]
    price_source: str


def _financial_input(seed: StockSeed) -> FinancialInput:
    return FinancialInput(
        seed.financials, seed.debt_to_equity, seed.promoter_pledge_pct, seed.is_lender
    )


def _sample(prices: list[float]) -> tuple[float, ...]:
    """Every few days over the last year, always ending on the latest close."""
    recent = prices[::-1][:HISTORY_SAMPLE_DAYS:HISTORY_SAMPLE_STEP]
    return tuple(round(p, 2) for p in reversed(recent))


def build_view(
    seed: StockSeed, closes: list[Close] | None, source: PriceSource, today: date
) -> StockView:
    """Pure: everything the table shows for one stock, from its seed and its closes."""
    financial, financial_needs = financial_score(_financial_input(seed))
    needs = list(financial_needs)
    if not source.official:
        needs.append(NEED_OFFICIAL_PRICES)
    if seed.lot_size is None:
        needs.append(NEED_LOT_SIZE)
    problems = int(not source.official) + int(bool(financial_needs))

    prices = [c.close for c in closes or []]
    high = reference_high(prices)
    if not closes or high is None:
        data_quality, score = evidence(0, financial, problems + 1)
        return StockView(
            seed, 0.0, "", 0.0, 0.0, 0, 0, 0.0, 0, 0.0, 0.0, 0, financial, data_quality, score,
            (NEED_PRICE_HISTORY, *needs), (), source.name,
        )  # fmt: skip

    days = [c.day for c in closes]
    start = next((i for i, d in enumerate(days) if d >= date.fromisoformat(METRICS_START)), 0)
    stats = recovery_stats(fall_events(prices, start_index=start))
    drawdown = max_drawdown_pct(prices[start:])
    years = history_years(days)
    stability, stability_needs = stability_score(
        StabilityInput(
            stats.count,
            stats.recovered_within_pct,
            stats.longest_days,
            stats.open_days,
            drawdown,
            years,
        )
    )
    stale = (today - days[-1]).days > STALE_AFTER_DAYS
    if stale:
        needs.append(NEED_FRESH_PRICES)
    problems += int(stale) + int(years < HISTORY_YEARS_RANGE[1])
    data_quality, score = evidence(stability, financial, problems)
    below = below_high_pct(prices[-1], high)
    return StockView(
        seed=seed,
        last_price=round(prices[-1], 2),
        price_as_of=days[-1].isoformat(),
        reference_high=round(high, 2),
        below_high_pct=round(below, 2),
        zone=zone(below),
        falls10=stats.count,
        recovered12m_pct=round(stats.recovered_within_pct or 0.0),
        longest_recovery_days=stats.longest_days,
        max_drawdown_pct=-round(drawdown),
        history_years=round(years, 1),
        stability=stability,
        financial=financial,
        data_quality=data_quality,
        evidence=score,
        needs=(*stability_needs, *needs),
        history=_sample(prices),
        price_source=source.name,
    )


class StockService:
    """Serves the stock table, refreshing prices at most once per TTL."""

    def __init__(self, seeds: list[StockSeed], prices: PriceSource, clock: Clock) -> None:
        self._seeds = seeds
        self._prices = prices
        self._clock = clock
        self._lock = threading.Lock()
        self._views: dict[str, StockView] = {}
        self._loaded_at: datetime | None = None

    def _closes(self, seed: StockSeed) -> list[Close] | None:
        try:
            closes = self._prices.daily_closes(seed.symbol)
            validate_closes([c.close for c in closes])
        except (PriceSourceError, ValueError):
            return None  # the row then says "needs data" instead of failing the whole table
        return closes

    def _fresh(self, now: datetime) -> bool:
        return (
            self._loaded_at is not None
            and (now - self._loaded_at).total_seconds() < PRICE_TTL_SECONDS
        )

    def _load(self) -> dict[str, StockView]:
        now = self._clock()
        with self._lock:
            if not self._fresh(now):
                with ThreadPoolExecutor(max_workers=MAX_FETCH_WORKERS) as pool:
                    closes = list(pool.map(self._closes, self._seeds))
                self._views = {
                    seed.symbol: build_view(seed, c, self._prices, now.date())
                    for seed, c in zip(self._seeds, closes, strict=True)
                }
                self._loaded_at = now
            return self._views

    def list_stocks(self) -> list[StockView]:
        return list(self._load().values())

    def get_stock(self, symbol: str) -> StockView:
        view = self._load().get(symbol.upper())
        if view is None:
            raise StockNotFoundError(symbol)
        return view

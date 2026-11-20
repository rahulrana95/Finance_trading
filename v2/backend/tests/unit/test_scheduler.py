"""The schedule: one run at start, then ticks that only work in market hours."""

from datetime import UTC, datetime

from steady.adapters.memory import MemoryStore
from steady.adapters.seed import load_seed_stocks
from steady.constants import (
    KIND_SCHEDULED,
    SCHEDULER_JOB_ID,
    SCHEDULER_START_JOB_ID,
    SCREENER_JOB_ID,
    SCREENER_START_JOB_ID,
)
from steady.scheduler import build_scheduler, scheduled_run
from steady.services.algo import AlgoService
from steady.services.screener import ScreenerService
from steady.services.stocks import StockService
from tests.support import FakePrices, closes

OPEN = datetime(2026, 11, 17, 7, 0, tzinfo=UTC)  # Tuesday 12:30 in India
CLOSED = datetime(2026, 11, 21, 7, 0, tzinfo=UTC)  # Saturday


def make(now: datetime) -> AlgoService:
    prices = FakePrices(default=closes([100.0] * 63))
    return AlgoService(
        StockService(load_seed_stocks(), prices, lambda: now), MemoryStore(), lambda: now
    )


def test_a_tick_in_market_hours_runs_the_algo():
    algo = make(OPEN)
    assert scheduled_run(algo, lambda: OPEN) is True
    assert [r.kind for r in algo.list_runs()] == [KIND_SCHEDULED]


def test_a_tick_outside_market_hours_does_nothing():
    algo = make(CLOSED)
    assert scheduled_run(algo, lambda: CLOSED) is False
    assert algo.list_runs() == []


def test_the_scheduler_has_a_start_run_and_a_five_minute_job():
    screener = ScreenerService([], FakePrices(), MemoryStore(), lambda: OPEN)
    scheduler = build_scheduler(make(OPEN), screener, lambda: OPEN)
    jobs = {job.id: job for job in scheduler.get_jobs()}
    assert set(jobs) == {
        SCHEDULER_START_JOB_ID,
        SCHEDULER_JOB_ID,
        SCREENER_START_JOB_ID,
        SCREENER_JOB_ID,
    }
    daily = str(jobs[SCREENER_JOB_ID].trigger)
    assert "hour='18'" in daily
    assert "minute='30'" in daily
    trigger = str(jobs[SCHEDULER_JOB_ID].trigger)
    assert "day_of_week='mon-fri'" in trigger
    assert "hour='9-15'" in trigger
    assert "minute='*/5'" in trigger
    assert str(scheduler.timezone) == "Asia/Kolkata"

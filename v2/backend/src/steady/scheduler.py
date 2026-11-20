"""Runs the algo by itself: once at start, then every few minutes while the market is open."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from steady.clock import Clock
from steady.constants import (
    KIND_SCHEDULED,
    MARKET_TIMEZONE,
    SCHEDULE_DAYS,
    SCHEDULE_HOURS,
    SCHEDULE_MINUTES,
    SCHEDULER_JOB_ID,
    SCHEDULER_START_JOB_ID,
    SCREEN_HOUR,
    SCREEN_MINUTE,
    SCREENER_JOB_ID,
    SCREENER_START_JOB_ID,
)
from steady.core.calendar import is_market_open
from steady.services.algo import AlgoService
from steady.services.screener import ScreenerService


def scheduled_run(algo: AlgoService, clock: Clock) -> bool:
    """One tick of the schedule. Does nothing outside market hours."""
    if not is_market_open(clock()):
        return False
    algo.run(KIND_SCHEDULED)
    return True


def build_scheduler(
    algo: AlgoService, screener: ScreenerService, clock: Clock
) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=MARKET_TIMEZONE)
    # Runs and ideas live in memory, so start with one run to have something to show.
    scheduler.add_job(algo.run, args=[KIND_SCHEDULED], id=SCHEDULER_START_JOB_ID)
    scheduler.add_job(
        scheduled_run,
        CronTrigger(
            day_of_week=SCHEDULE_DAYS,
            hour=SCHEDULE_HOURS,
            minute=SCHEDULE_MINUTES,
            timezone=MARKET_TIMEZONE,
        ),
        args=[algo, clock],
        id=SCHEDULER_JOB_ID,
        max_instances=1,
        coalesce=True,
    )
    # The screen fetches every stock, so it runs once after the close, and at start only if stale.
    scheduler.add_job(screener.run_if_stale, id=SCREENER_START_JOB_ID)
    scheduler.add_job(
        screener.run,
        CronTrigger(
            day_of_week=SCHEDULE_DAYS,
            hour=SCREEN_HOUR,
            minute=SCREEN_MINUTE,
            timezone=MARKET_TIMEZONE,
        ),
        id=SCREENER_JOB_ID,
        max_instances=1,
        coalesce=True,
    )
    return scheduler

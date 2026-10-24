"""Download a date range of NSE F&O bhavcopy files. Resumable and idempotent.

Usage:
    uv run python -m fintrade.services.bhavcopy_download --start 2019-02-11 --end 2026-10-23
"""

import argparse
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import httpx
import structlog

from fintrade.adapters.nse.bhavcopy import NIFTY_WEEKLY_OPTIONS_START, BhavcopyFetcher
from fintrade.adapters.nse.raw_store import ManifestRecord, RawStore, RecordStatus
from fintrade.adapters.system_clock import SystemClock
from fintrade.core.dates import weekdays
from fintrade.core.errors import DataError
from fintrade.ports.clock import Clock
from fintrade.services.logging_setup import configure_logging

DEFAULT_ROOT = Path("data/raw/nse_fo_bhavcopy")
POLITE_DELAY_SECONDS = 1.0

log = structlog.get_logger(__name__)


@dataclass
class DownloadSummary:
    downloaded: list[date] = field(default_factory=list)
    not_found: list[date] = field(default_factory=list)
    skipped: list[date] = field(default_factory=list)
    failed: list[date] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class DownloadJob:
    fetcher: BhavcopyFetcher
    store: RawStore
    clock: Clock
    sleep: Callable[[float], None]
    retry_not_found: bool = False


def download_range(job: DownloadJob, start: date, end: date) -> DownloadSummary:
    """Fetch every weekday in [start, end]. Days already stored and intact are skipped.

    A failed day is logged and counted, never silently dropped; the run continues so
    one bad day does not block the rest. Re-running retries failed days.
    """
    summary = DownloadSummary()
    latest = job.store.latest()
    for day in weekdays(start, end):
        record = latest.get(day.isoformat())
        if record is not None and _already_done(job, record):
            summary.skipped.append(day)
            continue
        try:
            fetched = job.fetcher.fetch(day)
        except DataError as exc:
            log.exception("bhavcopy_failed", day=day.isoformat(), error=str(exc))
            summary.failed.append(day)
            continue
        if fetched.content is None:
            job.store.mark_not_found(day, fetched.url, job.clock.now())
            summary.not_found.append(day)
        else:
            job.store.save(day, fetched.url, fetched.content, job.clock.now())
            summary.downloaded.append(day)
        job.sleep(POLITE_DELAY_SECONDS)
    log.info(
        "bhavcopy_range_done",
        downloaded=len(summary.downloaded),
        not_found=len(summary.not_found),
        skipped=len(summary.skipped),
        failed=len(summary.failed),
    )
    return summary


def _already_done(job: DownloadJob, record: ManifestRecord) -> bool:
    if record.status is RecordStatus.NOT_FOUND:
        return not job.retry_not_found
    return job.store.is_intact(record)


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", type=date.fromisoformat, default=NIFTY_WEEKLY_OPTIONS_START)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--retry-not-found", action="store_true")
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    client_factory: Callable[[], httpx.Client] = httpx.Client,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    configure_logging()
    with client_factory() as client:
        job = DownloadJob(
            fetcher=BhavcopyFetcher(client, sleep=sleep),
            store=RawStore(args.root),
            clock=SystemClock(),
            sleep=sleep,
            retry_not_found=args.retry_not_found,
        )
        summary = download_range(job, args.start, args.end)
    return 1 if summary.failed else 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point; main() is tested directly
    sys.exit(main())

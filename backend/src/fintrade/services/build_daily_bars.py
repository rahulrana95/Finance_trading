"""Build curated daily bars (Parquet) from the raw bhavcopy store.

Fail closed: a day with validation errors is NOT written; it is reported instead.
Idempotent: a day is rebuilt only when its raw file checksum changed (or with --force).

Usage:
    uv run python -m fintrade.services.build_daily_bars
"""

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import structlog

from fintrade.adapters.nse.bhavcopy_parser import parse_bhavcopy
from fintrade.adapters.nse.raw_store import RawStore, RecordStatus
from fintrade.adapters.parquet.daily_bars import DailyBarStore
from fintrade.core.errors import DataError
from fintrade.core.quality.bar_checks import Severity, check_day
from fintrade.services.bhavcopy_download import DEFAULT_ROOT as RAW_ROOT
from fintrade.services.logging_setup import configure_logging

CURATED_ROOT = Path("data/curated/nifty_daily_bars")

log = structlog.get_logger(__name__)


@dataclass
class BuildSummary:
    written: list[date] = field(default_factory=list)
    unchanged: list[date] = field(default_factory=list)
    rejected: dict[date, str] = field(default_factory=dict)


def build(raw: RawStore, curated: DailyBarStore, *, force: bool = False) -> BuildSummary:
    summary = BuildSummary()
    for day_text, record in sorted(raw.latest().items()):
        if record.status is not RecordStatus.OK or record.sha256 is None:
            continue
        day = date.fromisoformat(day_text)
        if not force and curated.source_sha256(day) == record.sha256:
            summary.unchanged.append(day)
            continue
        try:
            bars = parse_bhavcopy(raw.load(record), day)
        except DataError as exc:
            summary.rejected[day] = f"parse: {exc}"
            continue
        errors = [i for i in check_day(day, bars) if i.severity is Severity.ERROR]
        if errors:
            summary.rejected[day] = f"{len(errors)} validation errors, first: {errors[0].code}"
            continue
        curated.write_day(day, bars, record.sha256)
        summary.written.append(day)
    for day, reason in summary.rejected.items():
        log.error("daily_bars_rejected", day=day.isoformat(), reason=reason)
    log.info(
        "daily_bars_built",
        written=len(summary.written),
        unchanged=len(summary.unchanged),
        rejected=len(summary.rejected),
    )
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw-root", type=Path, default=RAW_ROOT)
    parser.add_argument("--curated-root", type=Path, default=CURATED_ROOT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    configure_logging()
    summary = build(RawStore(args.raw_root), DailyBarStore(args.curated_root), force=args.force)
    return 1 if summary.rejected else 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point; main() is tested directly
    sys.exit(main())

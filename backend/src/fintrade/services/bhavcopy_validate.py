"""Validate every downloaded bhavcopy day and write a quality report.

Usage:
    uv run python -m fintrade.services.bhavcopy_validate
Exit code 1 if any day has errors or could not be parsed.
"""

import argparse
import json
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import structlog

from fintrade.adapters.nse.bhavcopy_parser import parse_bhavcopy
from fintrade.adapters.nse.raw_store import RawStore, RecordStatus
from fintrade.core.errors import DataError
from fintrade.core.quality.bar_checks import Issue, Severity, check_day
from fintrade.services.bhavcopy_download import DEFAULT_ROOT
from fintrade.services.logging_setup import configure_logging

DEFAULT_REPORT = Path("data/reports/bhavcopy_quality.json")

log = structlog.get_logger(__name__)


@dataclass
class QualityReport:
    days_checked: int = 0
    not_found_days: list[str] = field(default_factory=list)
    parse_failures: dict[str, str] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(issue.severity is Severity.ERROR for issue in self.issues)

    @property
    def passed(self) -> bool:
        return not self.parse_failures and self.error_count == 0

    def summary(self) -> dict[str, object]:
        by_code = Counter(f"{issue.severity}:{issue.code}" for issue in self.issues)
        return {
            "days_checked": self.days_checked,
            "not_found_days": len(self.not_found_days),
            "parse_failures": len(self.parse_failures),
            "errors": self.error_count,
            "warnings": len(self.issues) - self.error_count,
            "by_code": dict(sorted(by_code.items())),
            "passed": self.passed,
        }


def validate_store(store: RawStore, symbol: str = "NIFTY") -> QualityReport:
    report = QualityReport()
    for day_text, record in sorted(store.latest().items()):
        if record.status is RecordStatus.NOT_FOUND:
            report.not_found_days.append(day_text)
            continue
        try:
            bars = parse_bhavcopy(store.load(record), date.fromisoformat(day_text), symbol)
        except DataError as exc:
            report.parse_failures[day_text] = str(exc)
            continue
        report.days_checked += 1
        report.issues += check_day(date.fromisoformat(day_text), bars)
    return report


def write_report(report: QualityReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": report.summary(),
        "not_found_days": report.not_found_days,
        "parse_failures": report.parse_failures,
        "issues": [asdict(issue) for issue in report.issues],
    }
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    configure_logging()
    report = validate_store(RawStore(args.root))
    write_report(report, args.report)
    log.info("bhavcopy_quality", report=str(args.report), **report.summary())
    return 0 if report.passed else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point; main() is tested directly
    sys.exit(main())

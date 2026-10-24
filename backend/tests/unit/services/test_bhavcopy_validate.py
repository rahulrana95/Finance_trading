import json
from datetime import UTC, date, datetime
from pathlib import Path

from fintrade.adapters.nse.raw_store import RawStore
from fintrade.services import bhavcopy_validate
from fintrade.services.bhavcopy_validate import validate_store
from tests.support.bhavcopy import UDIFF_HEADER, bhavcopy_zip, udiff_future_row, udiff_row

AT = datetime(2026, 10, 24, 16, 0, tzinfo=UTC)
URL = "https://example.test/f.zip"


def _clean_rows(day: str) -> list[dict[str, str]]:
    common = {"TradDt": day, "XpryDt": "2024-07-11"}
    return [udiff_future_row(**common), udiff_row(**common), udiff_row(OptnTp="PE", **common)]


def _store(tmp_path: Path) -> RawStore:
    store = RawStore(tmp_path / "raw")
    store.save(date(2024, 7, 5), URL, bhavcopy_zip(UDIFF_HEADER, _clean_rows("2024-07-05")), AT)
    store.mark_not_found(date(2024, 7, 6), URL, AT)
    return store


def test_clean_store_passes(tmp_path: Path) -> None:
    report = validate_store(_store(tmp_path))
    assert report.passed
    assert report.days_checked == 1
    assert report.not_found_days == ["2024-07-06"]
    assert report.summary()["errors"] == 0


def test_bad_rows_and_unparseable_days_fail(tmp_path: Path) -> None:
    store = _store(tmp_path)
    rows = _clean_rows("2024-07-08")
    rows[1] = rows[1] | {"HghPric": "1.00", "LwPric": "2.00"}
    store.save(date(2024, 7, 8), URL, bhavcopy_zip(UDIFF_HEADER, rows), AT)
    store.save(date(2024, 7, 9), URL, b"not a zip", AT)
    report = validate_store(store)
    assert not report.passed
    assert report.error_count == 1
    assert list(report.parse_failures) == ["2024-07-09"]
    assert report.summary()["by_code"] == {"error:high_below_low": 1}


def test_parse_failure_alone_fails_the_report(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    store.save(date(2024, 7, 9), URL, b"not a zip", AT)
    report = validate_store(store)
    assert report.error_count == 0
    assert not report.passed


def test_main_writes_report_and_sets_exit_code(tmp_path: Path) -> None:
    store = _store(tmp_path)
    report_path = tmp_path / "reports" / "q.json"
    args = ["--root", str(tmp_path / "raw"), "--report", str(report_path)]
    assert bhavcopy_validate.main(args) == 0
    payload = json.loads(report_path.read_text())
    assert payload["summary"]["passed"] is True
    assert payload["not_found_days"] == ["2024-07-06"]
    store.save(date(2024, 7, 9), URL, b"broken", AT)
    assert bhavcopy_validate.main(args) == 1
    assert "2024-07-09" in json.loads(report_path.read_text())["parse_failures"]

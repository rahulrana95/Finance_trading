from datetime import UTC, date, datetime
from pathlib import Path

from fintrade.adapters.nse.raw_store import RawStore
from fintrade.adapters.parquet.daily_bars import DailyBarStore
from fintrade.services import build_daily_bars
from fintrade.services.build_daily_bars import build
from tests.support.bhavcopy import UDIFF_HEADER, bhavcopy_zip, udiff_future_row, udiff_row

AT = datetime(2026, 10, 24, 16, 0, tzinfo=UTC)
URL = "https://example.test/f.zip"
GOOD_DAY, BAD_DAY, BROKEN_DAY = date(2024, 7, 5), date(2024, 7, 8), date(2024, 7, 9)


def _day_zip(day: date, *, bad: bool = False) -> bytes:
    common = {"TradDt": day.isoformat(), "XpryDt": "2024-07-11"}
    call = udiff_row(**common) | ({"HghPric": "1.00", "LwPric": "2.00"} if bad else {})
    return bhavcopy_zip(UDIFF_HEADER, [udiff_future_row(**common), call,
                                       udiff_row(OptnTp="PE", **common)])  # fmt: skip


def _stores(tmp_path: Path) -> tuple[RawStore, DailyBarStore]:
    raw = RawStore(tmp_path / "raw")
    raw.save(GOOD_DAY, URL, _day_zip(GOOD_DAY), AT)
    raw.mark_not_found(date(2024, 7, 6), URL, AT)
    return raw, DailyBarStore(tmp_path / "curated")


def test_good_day_written_and_readable(tmp_path: Path) -> None:
    raw, curated = _stores(tmp_path)
    summary = build(raw, curated)
    assert summary.written == [GOOD_DAY]
    assert len(curated.read_day(GOOD_DAY)) == 3


def test_second_build_is_a_no_op(tmp_path: Path) -> None:
    raw, curated = _stores(tmp_path)
    build(raw, curated)
    summary = build(raw, curated)
    assert summary.unchanged == [GOOD_DAY]
    assert summary.written == []


def test_force_rebuilds(tmp_path: Path) -> None:
    raw, curated = _stores(tmp_path)
    build(raw, curated)
    assert build(raw, curated, force=True).written == [GOOD_DAY]


def test_changed_source_is_rebuilt(tmp_path: Path) -> None:
    raw, curated = _stores(tmp_path)
    build(raw, curated)
    rows = [udiff_future_row(TradDt="2024-07-05", XpryDt="2024-07-11")]
    raw.save(GOOD_DAY, URL, bhavcopy_zip(UDIFF_HEADER, rows), AT)
    summary = build(raw, curated)
    assert summary.rejected[GOOD_DAY].startswith("1 validation errors")  # no options now
    assert len(curated.read_day(GOOD_DAY)) == 3  # old good data kept, not overwritten


def test_bad_and_unparseable_days_rejected_not_written(tmp_path: Path) -> None:
    raw, curated = _stores(tmp_path)
    raw.save(BAD_DAY, URL, _day_zip(BAD_DAY, bad=True), AT)
    raw.save(BROKEN_DAY, URL, b"not a zip", AT)
    summary = build(raw, curated)
    assert summary.written == [GOOD_DAY]
    assert "high_below_low" in summary.rejected[BAD_DAY]
    assert summary.rejected[BROKEN_DAY].startswith("parse:")
    assert curated.source_sha256(BAD_DAY) is None


def test_main_exit_codes(tmp_path: Path) -> None:
    raw, _ = _stores(tmp_path)
    args = ["--raw-root", str(tmp_path / "raw"), "--curated-root", str(tmp_path / "curated")]
    assert build_daily_bars.main(args) == 0
    raw.save(BROKEN_DAY, URL, b"not a zip", AT)
    assert build_daily_bars.main([*args, "--force"]) == 1

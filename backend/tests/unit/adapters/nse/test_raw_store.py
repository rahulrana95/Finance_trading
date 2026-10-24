import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from fintrade.adapters.nse.raw_store import (
    MANIFEST_NAME,
    ManifestRecord,
    RawStore,
    RecordStatus,
    sha256_hex,
)
from fintrade.core.errors import DataError

DAY = date(2026, 10, 23)
URL = "https://example.test/f.zip"
AT = datetime(2026, 10, 23, 16, 0, tzinfo=UTC)


def test_save_writes_file_and_manifest(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    record = store.save(DAY, URL, b"zipbytes", AT)
    path = tmp_path / "2026" / "2026-10-23.csv.zip"
    assert path.read_bytes() == b"zipbytes"
    assert not path.with_suffix(".zip.part").exists()
    assert record.sha256 == sha256_hex(b"zipbytes")
    assert record.size_bytes == 8
    line = json.loads((tmp_path / MANIFEST_NAME).read_text().strip())
    assert line["status"] == "ok"
    assert line["day"] == "2026-10-23"


def test_latest_returns_last_record_per_day(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    store.mark_not_found(DAY, URL, AT)
    store.save(DAY, URL, b"v2", AT)
    store.mark_not_found(date(2026, 10, 2), URL, AT)
    latest = store.latest()
    assert latest["2026-10-23"].status is RecordStatus.OK
    assert latest["2026-10-02"].status is RecordStatus.NOT_FOUND
    assert len((tmp_path / MANIFEST_NAME).read_text().splitlines()) == 3  # append-only


def test_latest_empty_when_no_manifest(tmp_path: Path) -> None:
    assert RawStore(tmp_path / "missing").latest() == {}


def test_blank_manifest_lines_ignored(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    store.save(DAY, URL, b"x", AT)
    with (tmp_path / MANIFEST_NAME).open("a") as f:
        f.write("\n   \n")
    assert list(store.latest()) == ["2026-10-23"]


@pytest.mark.parametrize(
    "bad_line",
    [
        "{not json",
        '{"day": "2026-10-23"}',
        '{"day": "x", "status": "weird", "url": "u", "fetched_at": "t"}',
        '{"day": "x", "status": "ok", "url": "u", "fetched_at": "t", "z": 1}',
    ],
)
def test_bad_manifest_line_raises(tmp_path: Path, bad_line: str) -> None:
    (tmp_path / MANIFEST_NAME).write_text(bad_line + "\n")
    with pytest.raises(DataError, match="bad manifest line 1"):
        RawStore(tmp_path).latest()


def test_intact_file_detected(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    record = store.save(DAY, URL, b"good", AT)
    assert store.is_intact(record)


def test_tampered_or_missing_file_not_intact(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    record = store.save(DAY, URL, b"good", AT)
    store.path_for(DAY).write_bytes(b"tampered")
    assert not store.is_intact(record)
    store.path_for(DAY).unlink()
    assert not store.is_intact(record)


def test_not_found_record_is_never_intact(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    record = store.mark_not_found(DAY, URL, AT)
    assert isinstance(record, ManifestRecord)
    assert not store.is_intact(record)


def test_load_returns_verified_content(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    record = store.save(DAY, URL, b"good", AT)
    assert store.load(record) == b"good"


def test_load_refuses_tampered_missing_or_not_found(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    record = store.save(DAY, URL, b"good", AT)
    store.path_for(DAY).write_bytes(b"bad")
    with pytest.raises(DataError, match="checksum mismatch"):
        store.load(record)
    store.path_for(DAY).unlink()
    with pytest.raises(DataError, match="stored file missing"):
        store.load(record)
    with pytest.raises(DataError, match="no stored file"):
        store.load(store.mark_not_found(DAY, URL, AT))

from dataclasses import replace
from datetime import date
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from fintrade.adapters.parquet.daily_bars import DailyBarStore, bars_to_table
from fintrade.core.errors import DataError
from tests.support.bars import DAY, clean_day

SHA = "ab" * 32


def test_write_then_read_day(tmp_path: Path) -> None:
    store = DailyBarStore(tmp_path)
    store.write_day(DAY, clean_day(), SHA)
    assert store.read_day(DAY) == clean_day()
    assert store.source_sha256(DAY) == SHA
    path = store.path_for(DAY)
    assert path == tmp_path / "2026" / "2026-10-23.parquet"
    assert not path.with_suffix(".parquet.part").exists()


def test_rewrite_replaces_content(tmp_path: Path) -> None:
    store = DailyBarStore(tmp_path)
    store.write_day(DAY, clean_day(), SHA)
    store.write_day(DAY, clean_day()[:1], "cd" * 32)
    assert len(store.read_day(DAY)) == 1
    assert store.source_sha256(DAY) == "cd" * 32


def test_bars_from_another_day_rejected(tmp_path: Path) -> None:
    wrong = [replace(bar, trade_date=date(2026, 10, 22)) for bar in clean_day()]
    with pytest.raises(DataError, match="written under 2026-10-23"):
        DailyBarStore(tmp_path).write_day(DAY, wrong, SHA)


def test_missing_day(tmp_path: Path) -> None:
    store = DailyBarStore(tmp_path)
    assert store.source_sha256(DAY) is None
    with pytest.raises(DataError, match="no curated bars"):
        store.read_day(DAY)


def test_file_without_source_metadata(tmp_path: Path) -> None:
    store = DailyBarStore(tmp_path)
    path = store.path_for(DAY)
    path.parent.mkdir(parents=True)
    pq.write_table(bars_to_table(clean_day()), path)
    assert store.source_sha256(DAY) is None
    assert store.read_day(DAY) == clean_day()


def test_read_range_skips_days_without_files(tmp_path: Path) -> None:
    store = DailyBarStore(tmp_path)
    friday, tuesday = date(2026, 10, 23), date(2026, 10, 27)
    store.write_day(friday, clean_day(), SHA)
    store.write_day(tuesday, [replace(b, trade_date=tuesday) for b in clean_day()], SHA)
    bars = store.read_range(date(2026, 10, 22), date(2026, 10, 27))
    assert sorted({b.trade_date for b in bars}) == [friday, tuesday]
    assert len(bars) == 6

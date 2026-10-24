import json
from pathlib import Path

from fintrade.adapters.parquet.daily_bars import DailyBarStore
from fintrade.core.bars import OptionType
from fintrade.services import derive_contract_specs
from tests.support.bars import DAY, clean_day, make_bar

SHA = "ab" * 32


def _args(tmp_path: Path) -> list[str]:
    return [
        "--start",
        "2026-10-01",
        "--end",
        "2026-10-31",
        "--curated-root",
        str(tmp_path / "curated"),
        "--output",
        str(tmp_path / "specs.json"),
    ]


def test_main_writes_specs(tmp_path: Path) -> None:
    DailyBarStore(tmp_path / "curated").write_day(DAY, clean_day(), SHA)
    assert derive_contract_specs.main(_args(tmp_path)) == 0
    (row,) = json.loads((tmp_path / "specs.json").read_text())
    assert row["expiry"] == "2026-10-27"
    assert row["lot_size"] == 65
    assert row["source"] == "stated"


def test_main_returns_1_on_inconsistent_data(tmp_path: Path) -> None:
    bad = [make_bar(), make_bar(lot_size=75, option_type=OptionType.PUT)]
    DailyBarStore(tmp_path / "curated").write_day(DAY, bad, SHA)
    assert derive_contract_specs.main(_args(tmp_path)) == 1
    assert not (tmp_path / "specs.json").exists()

"""Curated daily bars on disk: one Parquet file per trading day.

Layout:  <root>/<year>/<yyyy-mm-dd>.parquet
Each file records the SHA-256 of the raw file it was built from, so rebuilds are
idempotent: a day is rewritten only when its source changed.
Money and prices are stored as exact decimals, never floats.
"""

from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from fintrade.core.bars import ContractKind, DailyContractBar, OptionType
from fintrade.core.dates import weekdays
from fintrade.core.errors import DataError

FILE_SUFFIX = ".parquet"
SOURCE_SHA_KEY = b"source_sha256"
_PRICE: pa.DataType = pa.decimal128(18, 4)
_MONEY: pa.DataType = pa.decimal128(22, 4)

_FIELDS: "list[pa.Field[Any]]" = [  # quoted: pa.Field is not subscriptable at runtime
    pa.field("trade_date", pa.date32()),
    pa.field("symbol", pa.string()),
    pa.field("kind", pa.string()),
    pa.field("expiry", pa.date32()),
    pa.field("strike", _PRICE),
    pa.field("option_type", pa.string()),
    pa.field("open", _PRICE),
    pa.field("high", _PRICE),
    pa.field("low", _PRICE),
    pa.field("close", _PRICE),
    pa.field("settle", _PRICE),
    pa.field("last", _PRICE),
    pa.field("contracts_traded", pa.int64()),
    pa.field("turnover_rupees", _MONEY),
    pa.field("open_interest", pa.int64()),
    pa.field("change_in_oi", pa.int64()),
    pa.field("underlying", _PRICE),
    pa.field("lot_size", pa.int32()),
]
SCHEMA = pa.schema(_FIELDS)


def _bar_to_row(bar: DailyContractBar) -> dict[str, Any]:
    row = {name: getattr(bar, name) for name in SCHEMA.names}
    row["kind"] = bar.kind.value
    row["option_type"] = bar.option_type.value if bar.option_type is not None else None
    return row


def bars_to_table(bars: Iterable[DailyContractBar]) -> pa.Table:
    try:
        return pa.Table.from_pylist([_bar_to_row(bar) for bar in bars], schema=SCHEMA)
    except (pa.ArrowInvalid, pa.ArrowTypeError) as exc:
        raise DataError(f"bars do not fit the Parquet schema: {exc}") from exc


def table_to_bars(table: pa.Table) -> list[DailyContractBar]:
    if not table.schema.equals(SCHEMA):
        raise DataError(f"unexpected Parquet schema: {table.schema}")
    return [_row_to_bar(row) for row in table.to_pylist()]


def _row_to_bar(row: dict[str, Any]) -> DailyContractBar:
    option_type = row["option_type"]
    return DailyContractBar(
        **{
            **row,
            "kind": ContractKind(row["kind"]),
            "option_type": OptionType(option_type) if option_type is not None else None,
        }
    )


class DailyBarStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    def path_for(self, day: date) -> Path:
        return self._root / str(day.year) / f"{day.isoformat()}{FILE_SUFFIX}"

    def write_day(self, day: date, bars: Iterable[DailyContractBar], source_sha256: str) -> None:
        bar_list = list(bars)
        wrong_day = {bar.trade_date for bar in bar_list} - {day}
        if wrong_day:
            raise DataError(f"bars for {sorted(wrong_day)} written under {day}")
        table = bars_to_table(bar_list).replace_schema_metadata(
            {SOURCE_SHA_KEY: source_sha256.encode()}
        )
        target = self.path_for(day)
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".part")
        pq.write_table(table, partial)
        partial.replace(target)

    def source_sha256(self, day: date) -> str | None:
        path = self.path_for(day)
        if not path.exists():
            return None
        metadata = pq.read_schema(path).metadata or {}
        value = metadata.get(SOURCE_SHA_KEY)
        return value.decode() if value is not None else None

    def read_day(self, day: date) -> list[DailyContractBar]:
        path = self.path_for(day)
        if not path.exists():
            raise DataError(f"no curated bars for {day}")
        table = pq.read_table(path).replace_schema_metadata(None)
        return table_to_bars(table)

    def read_range(self, start: date, end: date) -> list[DailyContractBar]:
        """All stored bars in [start, end]; days without a file (holidays) are skipped."""
        return [
            bar for day in weekdays(start, end) if self.path_for(day).exists()
            for bar in self.read_day(day)
        ]  # fmt: skip

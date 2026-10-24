from decimal import Decimal

import pyarrow as pa
import pytest

from fintrade.adapters.parquet.daily_bars import SCHEMA, bars_to_table, table_to_bars
from fintrade.core.errors import DataError
from tests.support.bars import clean_day, make_bar


def test_round_trip_is_exact_for_options_and_futures() -> None:
    bars = clean_day()
    assert table_to_bars(bars_to_table(bars)) == bars


def test_old_format_bars_with_missing_fields_round_trip() -> None:
    bar = make_bar(last=None, underlying=None, lot_size=None)
    assert table_to_bars(bars_to_table([bar])) == [bar]


def test_money_is_stored_as_decimal_not_float() -> None:
    table = bars_to_table([make_bar(close=Decimal("42.55"))])
    assert pa.types.is_decimal(table.schema.field("close").type)
    assert table.column("close").to_pylist() == [Decimal("42.5500")]


def test_empty_table_has_schema() -> None:
    table = bars_to_table([])
    assert table.num_rows == 0
    assert table.schema.equals(SCHEMA)


def test_value_that_does_not_fit_is_rejected() -> None:
    with pytest.raises(DataError, match="do not fit"):
        bars_to_table([make_bar(close=Decimal("1.123456"))])  # more than 4 decimals


def test_wrong_schema_rejected_on_read() -> None:
    table = pa.table({"close": [1.0]})
    with pytest.raises(DataError, match="unexpected Parquet schema"):
        table_to_bars(table)

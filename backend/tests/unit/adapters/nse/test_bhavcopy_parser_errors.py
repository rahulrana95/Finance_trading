"""Negative and edge cases: every bad input fails loudly with a DataError."""

from datetime import date

import pytest

from fintrade.adapters.nse.bhavcopy_parser import parse_bhavcopy
from fintrade.core.errors import DataError
from tests.support.bhavcopy import OLD_HEADER, UDIFF_HEADER, bhavcopy_zip, old_row, udiff_row
from tests.support.http import make_zip

DAY = date(2024, 7, 5)


def test_unknown_header_rejected() -> None:
    content = make_zip({"bhav.csv": b"FOO,BAR\n1,2\n"})
    with pytest.raises(DataError, match="unknown bhavcopy header"):
        parse_bhavcopy(content, DAY)


def test_header_missing_one_column_rejected() -> None:
    header = [c for c in UDIFF_HEADER if c != "SttlmPric"]
    row = {k: v for k, v in udiff_row().items() if k != "SttlmPric"}
    with pytest.raises(DataError, match="unknown bhavcopy header"):
        parse_bhavcopy(bhavcopy_zip(header, [row]), DAY)


@pytest.mark.parametrize(
    "override",
    [
        {"CLOSE": "abc"},
        {"CLOSE": ""},
        {"HIGH": "NaN"},
        {"CONTRACTS": "12.5"},
        {"OPEN_INT": "x"},
        {"EXPIRY_DT": "2024-07-11"},
        {"TIMESTAMP": "31-FEB-2024"},
        {"OPTION_TYP": "XX"},
    ],
)
def test_bad_old_values_rejected_with_line_number(override: dict[str, str]) -> None:
    rows = [old_row(), old_row(**override)]
    with pytest.raises(DataError, match="bad bhavcopy row at line 3"):
        parse_bhavcopy(bhavcopy_zip(OLD_HEADER, rows), DAY)


@pytest.mark.parametrize(
    "override",
    [{"StrkPric": ""}, {"OptnTp": "CA"}, {"XpryDt": "11-Jul-2024"}, {"NewBrdLotQty": "2.5"}],
)
def test_bad_udiff_values_rejected(override: dict[str, str]) -> None:
    with pytest.raises(DataError, match="bad bhavcopy row at line 2"):
        parse_bhavcopy(bhavcopy_zip(UDIFF_HEADER, [udiff_row(**override)]), DAY)


def test_trade_date_mismatch_rejected() -> None:
    with pytest.raises(DataError, match="trade date 2024-07-04 != expected 2024-07-05"):
        parse_bhavcopy(bhavcopy_zip(UDIFF_HEADER, [udiff_row(TradDt="2024-07-04")]), DAY)


def test_short_row_rejected() -> None:
    content = make_zip({"bhav.csv": (",".join(OLD_HEADER) + "\nOPTIDX,NIFTY\n").encode()})
    with pytest.raises(DataError, match="bad bhavcopy row"):
        parse_bhavcopy(content, DAY)


def test_not_a_zip_rejected() -> None:
    with pytest.raises(DataError, match="unreadable"):
        parse_bhavcopy(b"<html></html>", DAY)


def test_non_utf8_rejected() -> None:
    with pytest.raises(DataError, match="unreadable"):
        parse_bhavcopy(make_zip({"bhav.csv": b"\xff\xfe\x00bad"}), DAY)


def test_multiple_members_rejected() -> None:
    with pytest.raises(DataError, match="expected one CSV"):
        parse_bhavcopy(make_zip({"a.csv": b"x", "b.csv": b"y"}), DAY)

from datetime import date

import pytest

from fintrade.adapters.nse.bhavcopy import BhavcopyFormat, bhavcopy_url, format_for


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2019, 2, 11), BhavcopyFormat.OLD),
        (date(2024, 7, 5), BhavcopyFormat.OLD),  # last old-format day
        (date(2024, 7, 8), BhavcopyFormat.UDIFF),  # first UDiFF day
        (date(2026, 10, 23), BhavcopyFormat.UDIFF),
    ],
)
def test_format_switch_boundary(day: date, expected: BhavcopyFormat) -> None:
    assert format_for(day) is expected


def test_old_format_url() -> None:
    assert bhavcopy_url(date(2019, 2, 1)) == (
        "https://nsearchives.nseindia.com/content/historical/DERIVATIVES/2019/FEB/"
        "fo01FEB2019bhav.csv.zip"
    )


def test_udiff_url() -> None:
    assert bhavcopy_url(date(2024, 7, 8)) == (
        "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_20240708_F_0000.csv.zip"
    )


@pytest.mark.parametrize(("month", "abbr"), [(1, "JAN"), (6, "JUN"), (12, "DEC")])
def test_old_format_month_names(month: int, abbr: str) -> None:
    assert f"/2023/{abbr}/fo15{abbr}2023bhav" in bhavcopy_url(date(2023, month, 15))

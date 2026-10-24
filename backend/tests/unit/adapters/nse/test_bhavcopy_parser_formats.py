"""Positive cases: both formats parse into identical normalized bars."""

from datetime import date
from decimal import Decimal

from fintrade.adapters.nse.bhavcopy_parser import parse_bhavcopy
from fintrade.core.bars import ContractKind, OptionType
from tests.support.bhavcopy import (
    OLD_HEADER,
    UDIFF_HEADER,
    bhavcopy_zip,
    old_future_row,
    old_row,
    udiff_future_row,
    udiff_row,
)

DAY = date(2024, 7, 5)


def test_old_format_option_row() -> None:
    (bar,) = parse_bhavcopy(bhavcopy_zip(OLD_HEADER, [old_row()]), DAY)
    assert bar.kind is ContractKind.OPTION
    assert (bar.expiry, bar.strike, bar.option_type) == (
        date(2024, 7, 11),
        Decimal(23000),
        OptionType.CALL,
    )
    assert (bar.open, bar.high, bar.low, bar.close, bar.settle) == (
        Decimal(1304),
        Decimal(1378),
        Decimal(1190),
        Decimal(1340),
        Decimal(1340),
    )
    assert bar.contracts_traded == 1802
    assert bar.turnover_rupees == Decimal("1092807000")  # 10928.07 lakh
    assert (bar.open_interest, bar.change_in_oi) == (150500, -5700)
    assert (bar.last, bar.underlying, bar.lot_size) == (None, None, None)


def test_udiff_option_row_has_extra_fields() -> None:
    (bar,) = parse_bhavcopy(bhavcopy_zip(UDIFF_HEADER, [udiff_row()]), DAY)
    assert (bar.strike, bar.option_type, bar.close) == (
        Decimal(23000),
        OptionType.CALL,
        Decimal(1340),
    )
    assert bar.last == Decimal("1346.60")
    assert bar.underlying == Decimal("24323.85")
    assert bar.lot_size == 25
    assert bar.turnover_rupees == Decimal("1092807971.25")


def test_both_formats_agree_on_shared_fields() -> None:
    (old,) = parse_bhavcopy(bhavcopy_zip(OLD_HEADER, [old_row()]), DAY)
    (new,) = parse_bhavcopy(bhavcopy_zip(UDIFF_HEADER, [udiff_row()]), DAY)
    shared = ["trade_date", "expiry", "strike", "option_type", "open", "high", "low", "close"]
    shared += ["settle", "contracts_traded", "open_interest", "change_in_oi"]
    for field in shared:
        assert getattr(old, field) == getattr(new, field), field


def test_futures_have_no_strike_or_option_type() -> None:
    (old,) = parse_bhavcopy(bhavcopy_zip(OLD_HEADER, [old_future_row()]), DAY)
    (new,) = parse_bhavcopy(bhavcopy_zip(UDIFF_HEADER, [udiff_future_row()]), DAY)
    for bar in (old, new):
        assert bar.kind is ContractKind.FUTURE
        assert (bar.strike, bar.option_type) == (None, None)


def test_other_symbols_and_stock_contracts_filtered_out() -> None:
    rows = [
        old_row(),
        old_row(SYMBOL="BANKNIFTY"),
        old_row(INSTRUMENT="OPTSTK", SYMBOL="NIFTY"),
        old_row(OPTION_TYP="PE"),
    ]
    bars = parse_bhavcopy(bhavcopy_zip(OLD_HEADER, rows), DAY)
    assert [b.option_type for b in bars] == [OptionType.CALL, OptionType.PUT]


def test_symbol_parameter_selects_other_index() -> None:
    rows = [udiff_row(), udiff_row(TckrSymb="BANKNIFTY"), udiff_row(FinInstrmTp="STO")]
    bars = parse_bhavcopy(bhavcopy_zip(UDIFF_HEADER, rows), DAY, symbol="BANKNIFTY")
    assert [b.symbol for b in bars] == ["BANKNIFTY"]


def test_whitespace_and_bom_tolerated() -> None:
    content = bhavcopy_zip(OLD_HEADER, [old_row(SYMBOL=" NIFTY ", CLOSE=" 1340 ")])
    (bar,) = parse_bhavcopy(content, DAY)
    assert bar.close == Decimal(1340)


def test_empty_file_gives_no_bars() -> None:
    assert parse_bhavcopy(bhavcopy_zip(UDIFF_HEADER, []), DAY) == []

"""Parse NSE F&O bhavcopy (old or UDiFF format) into `DailyContractBar` rows.

The format is detected from the header, not the date, because NSE back-filled UDiFF
files for early 2024. Unknown headers fail loudly so a silent format change can't slip in.
Field meanings were checked by comparing both formats for 2024-07-05 (same values).
"""

import csv
import io
import zipfile
from collections.abc import Callable, Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from fintrade.core.bars import ContractKind, DailyContractBar, OptionType
from fintrade.core.errors import DataError

RUPEES_PER_LAKH = Decimal(100_000)

OLD_COLUMNS = frozenset((
    "INSTRUMENT", "SYMBOL", "EXPIRY_DT", "STRIKE_PR", "OPTION_TYP", "OPEN", "HIGH", "LOW",
    "CLOSE", "SETTLE_PR", "CONTRACTS", "VAL_INLAKH", "OPEN_INT", "CHG_IN_OI", "TIMESTAMP",
))  # fmt: skip
UDIFF_COLUMNS = frozenset((
    "TradDt", "FinInstrmTp", "TckrSymb", "XpryDt", "StrkPric", "OptnTp", "OpnPric", "HghPric",
    "LwPric", "ClsPric", "LastPric", "SttlmPric", "UndrlygPric", "TtlTradgVol", "TtlTrfVal",
    "OpnIntrst", "ChngInOpnIntrst", "NewBrdLotQty",
))  # fmt: skip
_OLD_KINDS = {"OPTIDX": ContractKind.OPTION, "FUTIDX": ContractKind.FUTURE}
_UDIFF_KINDS = {"IDO": ContractKind.OPTION, "IDF": ContractKind.FUTURE}
_OLD_DATE = "%d-%b-%Y"

type Row = Mapping[str, str]


def parse_bhavcopy(content: bytes, day: date, symbol: str = "NIFTY") -> list[DailyContractBar]:
    """Index options and futures for `symbol` traded on `day`."""
    rows = _read_csv(content)
    header = set(rows.fieldnames or ()) - {""}
    if header >= OLD_COLUMNS:
        parse_row, kinds, kind_col, symbol_col = _old_row, _OLD_KINDS, "INSTRUMENT", "SYMBOL"
    elif header >= UDIFF_COLUMNS:
        parse_row, kinds, kind_col, symbol_col = _udiff_row, _UDIFF_KINDS, "FinInstrmTp", "TckrSymb"
    else:
        raise DataError(f"unknown bhavcopy header for {day}: {sorted(header)}")
    return [
        _with_row_context(parse_row, row, kinds[row[kind_col].strip()], day, line)
        for line, row in enumerate(rows, start=2)
        if row[symbol_col].strip() == symbol and row[kind_col].strip() in kinds
    ]


def _read_csv(content: bytes) -> csv.DictReader[str]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = archive.namelist()
            if len(names) != 1:
                raise DataError(f"expected one CSV in zip, got {names}")
            text = archive.read(names[0]).decode("utf-8-sig")
    except (zipfile.BadZipFile, UnicodeDecodeError) as exc:
        raise DataError(f"unreadable bhavcopy: {exc}") from exc
    return csv.DictReader(io.StringIO(text), restval="")  # short rows fail as bad numbers


def _with_row_context(
    parse_row: Callable[[Row, ContractKind], DailyContractBar],
    row: Row,
    kind: ContractKind,
    day: date,
    line: int,
) -> DailyContractBar:
    try:
        bar = parse_row(row, kind)
    except (InvalidOperation, ValueError, KeyError) as exc:
        raise DataError(f"bad bhavcopy row at line {line} for {day}: {exc}") from exc
    if bar.trade_date != day:
        raise DataError(f"line {line}: trade date {bar.trade_date} != expected {day}")
    return bar


def _old_row(row: Row, kind: ContractKind) -> DailyContractBar:
    is_option = kind is ContractKind.OPTION
    return DailyContractBar(
        trade_date=datetime.strptime(row["TIMESTAMP"].strip(), _OLD_DATE).date(),  # noqa: DTZ007
        symbol=row["SYMBOL"].strip(),
        kind=kind,
        expiry=datetime.strptime(row["EXPIRY_DT"].strip(), _OLD_DATE).date(),  # noqa: DTZ007
        strike=_decimal(row["STRIKE_PR"]) if is_option else None,
        option_type=OptionType(row["OPTION_TYP"].strip()) if is_option else None,
        open=_decimal(row["OPEN"]),
        high=_decimal(row["HIGH"]),
        low=_decimal(row["LOW"]),
        close=_decimal(row["CLOSE"]),
        settle=_decimal(row["SETTLE_PR"]),
        last=None,
        contracts_traded=_int(row["CONTRACTS"]),
        turnover_rupees=_decimal(row["VAL_INLAKH"]) * RUPEES_PER_LAKH,
        open_interest=_int(row["OPEN_INT"]),
        change_in_oi=_int(row["CHG_IN_OI"]),
        underlying=None,
        lot_size=None,
    )


def _udiff_row(row: Row, kind: ContractKind) -> DailyContractBar:
    is_option = kind is ContractKind.OPTION
    return DailyContractBar(
        trade_date=date.fromisoformat(row["TradDt"].strip()),
        symbol=row["TckrSymb"].strip(),
        kind=kind,
        expiry=date.fromisoformat(row["XpryDt"].strip()),
        strike=_decimal(row["StrkPric"]) if is_option else None,
        option_type=OptionType(row["OptnTp"].strip()) if is_option else None,
        open=_decimal(row["OpnPric"]),
        high=_decimal(row["HghPric"]),
        low=_decimal(row["LwPric"]),
        close=_decimal(row["ClsPric"]),
        settle=_decimal(row["SttlmPric"]),
        last=_decimal(row["LastPric"]),
        contracts_traded=_int(row["TtlTradgVol"]),
        turnover_rupees=_decimal(row["TtlTrfVal"]),
        open_interest=_int(row["OpnIntrst"]),
        change_in_oi=_int(row["ChngInOpnIntrst"]),
        underlying=_decimal(row["UndrlygPric"]),
        lot_size=_int(row["NewBrdLotQty"]),
    )


def _decimal(text: str) -> Decimal:
    value = Decimal(text.strip())
    if not value.is_finite():
        raise ValueError(f"non-finite number {text!r}")
    return value


def _int(text: str) -> int:
    value = _decimal(text)
    if value != value.to_integral_value():
        raise ValueError(f"expected whole number, got {text!r}")
    return int(value)

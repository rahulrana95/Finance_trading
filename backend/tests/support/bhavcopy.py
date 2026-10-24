"""Builders for fake NSE bhavcopy files in both formats (values mirror real 2024-07-05 rows)."""

import csv
import io

from tests.support.http import make_zip

OLD_HEADER = [
    "INSTRUMENT", "SYMBOL", "EXPIRY_DT", "STRIKE_PR", "OPTION_TYP", "OPEN", "HIGH", "LOW",
    "CLOSE", "SETTLE_PR", "CONTRACTS", "VAL_INLAKH", "OPEN_INT", "CHG_IN_OI", "TIMESTAMP", "",
]  # fmt: skip
UDIFF_HEADER = [
    "TradDt", "BizDt", "Sgmt", "Src", "FinInstrmTp", "FinInstrmId", "ISIN", "TckrSymb",
    "SctySrs", "XpryDt", "FininstrmActlXpryDt", "StrkPric", "OptnTp", "FinInstrmNm", "OpnPric",
    "HghPric", "LwPric", "ClsPric", "LastPric", "PrvsClsgPric", "UndrlygPric", "SttlmPric",
    "OpnIntrst", "ChngInOpnIntrst", "TtlTradgVol", "TtlTrfVal", "TtlNbOfTxsExctd", "SsnId",
    "NewBrdLotQty", "Rmks", "Rsvd1", "Rsvd2", "Rsvd3", "Rsvd4",
]  # fmt: skip


def old_row(**overrides: str) -> dict[str, str]:
    row = {
        "INSTRUMENT": "OPTIDX", "SYMBOL": "NIFTY", "EXPIRY_DT": "11-Jul-2024",
        "STRIKE_PR": "23000", "OPTION_TYP": "CE", "OPEN": "1304", "HIGH": "1378",
        "LOW": "1190", "CLOSE": "1340", "SETTLE_PR": "1340", "CONTRACTS": "1802",
        "VAL_INLAKH": "10928.07", "OPEN_INT": "150500", "CHG_IN_OI": "-5700",
        "TIMESTAMP": "05-JUL-2024", "": "",
    }  # fmt: skip
    return row | overrides


def old_future_row(**overrides: str) -> dict[str, str]:
    return old_row(INSTRUMENT="FUTIDX", STRIKE_PR="0", OPTION_TYP="XX", **overrides)


def udiff_row(**overrides: str) -> dict[str, str]:
    row = {
        "TradDt": "2024-07-05", "BizDt": "2024-07-05", "Sgmt": "FO", "Src": "NSE",
        "FinInstrmTp": "IDO", "FinInstrmId": "1", "ISIN": "", "TckrSymb": "NIFTY",
        "SctySrs": "", "XpryDt": "2024-07-11", "FininstrmActlXpryDt": "2024-07-11",
        "StrkPric": "23000.00", "OptnTp": "CE", "FinInstrmNm": "NIFTY24JUL23000CE",
        "OpnPric": "1304.00", "HghPric": "1378.00", "LwPric": "1190.00", "ClsPric": "1340.00",
        "LastPric": "1346.60", "PrvsClsgPric": "1300.00", "UndrlygPric": "24323.85",
        "SttlmPric": "1340.00", "OpnIntrst": "150500", "ChngInOpnIntrst": "-5700",
        "TtlTradgVol": "1802", "TtlTrfVal": "1092807971.25", "TtlNbOfTxsExctd": "626",
        "SsnId": "F1", "NewBrdLotQty": "25", "Rmks": "", "Rsvd1": "", "Rsvd2": "",
        "Rsvd3": "", "Rsvd4": "",
    }  # fmt: skip
    return row | overrides


def udiff_future_row(**overrides: str) -> dict[str, str]:
    return udiff_row(FinInstrmTp="IDF", StrkPric="", OptnTp="", **overrides)


def bhavcopy_zip(header: list[str], rows: list[dict[str, str]]) -> bytes:
    text = io.StringIO()
    writer = csv.DictWriter(text, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return make_zip({"bhav.csv": text.getvalue().encode()})

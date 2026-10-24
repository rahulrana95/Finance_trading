"""Daily bar for one exchange contract (option or future), source-independent."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class ContractKind(StrEnum):
    OPTION = "option"
    FUTURE = "future"


class OptionType(StrEnum):
    CALL = "CE"
    PUT = "PE"


@dataclass(frozen=True, slots=True)
class DailyContractBar:
    trade_date: date
    symbol: str
    kind: ContractKind
    expiry: date
    strike: Decimal | None  # None for futures
    option_type: OptionType | None  # None for futures
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    settle: Decimal
    last: Decimal | None  # last traded price; not in the old NSE format
    contracts_traded: int
    turnover_rupees: Decimal
    open_interest: int  # in units (quantity), as NSE reports it
    change_in_oi: int
    underlying: Decimal | None  # not in the old NSE format
    lot_size: int | None  # not in the old NSE format

    @property
    def mark(self) -> Decimal:
        """Price to value the contract at: settle, or close when NSE reports no settle.

        Bhavcopies carry settle 0 for some far strikes that still have a close (about 2%
        of option bars before 2024-07); 0 there means "not reported", not "worthless".
        """
        return self.settle if self.settle > 0 else self.close

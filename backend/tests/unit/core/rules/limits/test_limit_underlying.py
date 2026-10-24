"""AGENTS.md section 1: Nifty 50 index options only."""

from datetime import date
from decimal import Decimal

from fintrade.core.bars import OptionType
from fintrade.core.instruments import CreditSpread, credit_spread
from fintrade.core.rules.entry import EntryRule, check_entry
from tests.support.rules import codes, good_account, good_entry


def _spread(symbol: str) -> CreditSpread:
    return credit_spread(
        symbol=symbol,
        expiry=date(2026, 11, 3),
        option_type=OptionType.PUT,
        short_strike=Decimal(51000),
        long_strike=Decimal(50800),
        lots=1,
    )


def test_nifty_allowed() -> None:
    assert check_entry(good_entry(_spread("NIFTY")), good_account()) == []


def test_other_underlying_blocked() -> None:
    entry = good_entry(_spread("BANKNIFTY"))
    assert codes(check_entry(entry, good_account())) == [EntryRule.UNDERLYING]

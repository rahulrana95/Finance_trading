from decimal import Decimal

from fintrade.core.rules.entry import EntryRule, check_entry
from tests.support.instruments import bull_put
from tests.support.rules import codes, good_account, good_entry


def test_clean_entry_passes_every_rule() -> None:
    assert check_entry(good_entry(), good_account()) == []
    assert check_entry(good_entry(bull_put()), good_account()) == []


def test_every_violation_is_reported_not_just_the_first() -> None:
    entry = good_entry(entry_expiry=None, max_loss=Decimal(500_000))
    account = good_account(open_positions=5, new_positions_today=1, loss_limit_hit=True)
    assert codes(check_entry(entry, account)) == [
        EntryRule.EXPIRY,
        EntryRule.LOSS_LIMIT_HIT,
        EntryRule.MAX_LOSS_BUDGET,
        EntryRule.OPEN_POSITIONS,
        EntryRule.NEW_POSITIONS_TODAY,
    ]

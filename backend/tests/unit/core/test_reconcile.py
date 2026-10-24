from dataclasses import replace
from decimal import Decimal

from fintrade.core.reconcile import Mismatch, net_units, reconcile
from tests.support.instruments import bull_put, iron_condor

LOT = 65


def test_net_units_signed_and_summed_across_positions() -> None:
    # Two positions sharing the 24600 put: the broker would show them netted.
    condor, spread = iron_condor(lots=1), bull_put(lots=2)
    totals = net_units([(leg, LOT) for p in (condor, spread) for leg in p.legs])
    assert totals[spread.short.contract] == -(1 + 2) * LOT
    assert totals[spread.long.contract] == (1 + 2) * LOT
    assert totals[condor.call_spread.short.contract] == -LOT


def test_matching_books_have_no_mismatch() -> None:
    spread = bull_put()
    ledger = net_units([(leg, LOT) for leg in spread.legs])
    assert reconcile(ledger, dict(ledger)) == []


def test_quantity_difference_reported() -> None:
    spread = bull_put()
    ledger = net_units([(leg, LOT) for leg in spread.legs])
    broker = dict(ledger) | {spread.short.contract: -65}
    assert reconcile(ledger, broker) == [Mismatch(spread.short.contract, -130, -65)]


def test_contract_missing_on_either_side_reported() -> None:
    spread = bull_put()
    unknown = replace(spread.short.contract, strike=Decimal(24000))
    ledger = net_units([(leg, LOT) for leg in spread.legs])
    broker = {spread.long.contract: 130, unknown: -65}
    assert reconcile(ledger, broker) == [
        Mismatch(unknown, 0, -65),
        Mismatch(spread.short.contract, -130, 0),
    ]


def test_empty_books_match() -> None:
    assert reconcile({}, {}) == []

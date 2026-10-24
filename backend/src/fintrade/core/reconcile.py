"""Compare our own ledger with the broker's net positions (MONITORING.md).

The broker nets quantities per contract; our ledger tracks legs per position. Summed per
contract, the two must agree exactly. Any difference blocks new orders (AGENTS.md section 2).
"""

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from fintrade.core.instruments import Leg, OptionContract, Side


@dataclass(frozen=True, slots=True)
class Mismatch:
    contract: OptionContract
    ledger_units: int  # signed: + long, - short
    broker_units: int


def net_units(legs: Iterable[tuple[Leg, int]]) -> Counter[OptionContract]:
    """Signed units per contract from (open leg, lot size) pairs."""
    totals: Counter[OptionContract] = Counter()
    for leg, lot_size in legs:
        units = leg.lots * lot_size
        totals[leg.contract] += units if leg.side is Side.BUY else -units
    return totals


def reconcile(
    ledger: Mapping[OptionContract, int], broker: Mapping[OptionContract, int]
) -> list[Mismatch]:
    """Every contract where signed units differ (a missing contract counts as 0)."""
    contracts = sorted(set(ledger) | set(broker), key=str)
    return [
        Mismatch(contract, ledger.get(contract, 0), broker.get(contract, 0))
        for contract in contracts
        if ledger.get(contract, 0) != broker.get(contract, 0)
    ]

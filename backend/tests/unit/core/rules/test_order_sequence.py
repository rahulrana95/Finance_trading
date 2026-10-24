"""AGENTS.md section 2: never leave a short leg unhedged, even for a moment."""

import pytest

from fintrade.core.instruments import Position, Side
from fintrade.core.rules.order_sequence import entry_sequence, exit_sequence
from tests.support.instruments import bear_call, bull_put, iron_condor

POSITIONS = [bull_put(), bear_call(), iron_condor()]


def _sides(legs: list) -> list[Side]:  # type: ignore[type-arg]
    return [leg.side for leg in legs]


@pytest.mark.parametrize("position", POSITIONS)
def test_entry_buys_every_hedge_before_any_short(position: Position) -> None:
    sides = _sides(entry_sequence(position))
    first_sell = sides.index(Side.SELL)
    assert Side.SELL not in sides[:first_sell]
    assert Side.BUY not in sides[first_sell:]


@pytest.mark.parametrize("position", POSITIONS)
def test_exit_closes_every_short_before_any_hedge(position: Position) -> None:
    sides = _sides(exit_sequence(position))
    first_buy = sides.index(Side.BUY)
    assert Side.BUY not in sides[:first_buy]
    assert Side.SELL not in sides[first_buy:]


@pytest.mark.parametrize("position", POSITIONS)
def test_sequences_contain_every_leg_exactly_once(position: Position) -> None:
    assert sorted(map(id, entry_sequence(position))) == sorted(map(id, position.legs))
    assert sorted(map(id, exit_sequence(position))) == sorted(map(id, position.legs))


def test_iron_condor_golden_order() -> None:
    condor = iron_condor()
    put, call = condor.put_spread, condor.call_spread
    assert entry_sequence(condor) == [put.long, call.long, put.short, call.short]
    assert exit_sequence(condor) == [put.short, call.short, put.long, call.long]

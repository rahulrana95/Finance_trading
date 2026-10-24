"""AGENTS.md section 5: no look-ahead. The guard makes future data unreachable."""

from datetime import date

import pytest

from fintrade.backtest.data import (
    GuardedMarketData,
    LookAheadError,
    option_contract,
    relabel_expiries,
)
from fintrade.core.errors import DataError
from tests.support.backtest import market, spread_bars
from tests.support.bars import make_future
from tests.support.instruments import bull_put

D1, D2 = date(2026, 10, 26), date(2026, 10, 27)


def _guarded() -> GuardedMarketData:
    spread = bull_put()
    return GuardedMarketData(market(spread_bars(spread, {D1: ("40", "10"), D2: ("35", "9")})))


def test_today_and_past_are_readable() -> None:
    data = _guarded()
    data.advance_to(D1)
    assert len(data.option_bars(D1)) == 2
    data.advance_to(D2)
    assert len(data.option_bars(D1)) == 2
    assert len(data.option_bars(D2)) == 2
    assert list(data.trading_days()) == [D1, D2]


def test_future_day_is_unreachable() -> None:
    data = _guarded()
    data.advance_to(D1)
    with pytest.raises(LookAheadError, match="asked for 2026-10-27 while replaying 2026-10-26"):
        data.option_bars(D2)


def test_nothing_readable_before_replay_starts() -> None:
    with pytest.raises(LookAheadError):
        _guarded().option_bars(D1)


@pytest.mark.parametrize("second", [D1, date(2026, 10, 23)])
def test_replay_cannot_go_backwards_or_repeat(second: date) -> None:
    data = _guarded()
    data.advance_to(D1)
    with pytest.raises(DataError, match="replay must move forward"):
        data.advance_to(second)


def test_futures_ignored_and_missing_day_is_empty() -> None:
    data = market([make_future(trade_date=D1)])
    assert data.trading_days() == []
    assert data.option_bars(D1) == {}


def test_option_contract_rejects_future_bar() -> None:
    with pytest.raises(DataError, match="not an option bar"):
        option_contract(make_future())


def test_relabel_expiries_gives_one_contract_one_identity() -> None:
    old, new = date(2023, 6, 29), date(2023, 6, 28)
    bars = [make_future(expiry=old), make_future(expiry=date(2023, 7, 27))]
    out = list(relabel_expiries(bars, {old: new}))
    assert [b.expiry for b in out] == [new, date(2023, 7, 27)]
    assert out[1] is bars[1]

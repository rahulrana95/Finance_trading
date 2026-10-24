"""P&L attribution adds up exactly, and each Greek explains the move it should."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from fintrade.backtest.attribution import PnlAttribution, attribute
from fintrade.backtest.data import InMemoryMarketData
from fintrade.backtest.fills import BarFillModel, FillConfig, ProportionalSpread
from fintrade.backtest.trades import ClosedTrade, FillModel, Ticket, close_trade, open_trade
from fintrade.core.errors import DataError
from tests.support.backtest import SettleFill
from tests.support.chain import FORWARD, VOL, chain_history
from tests.support.instruments import EXPIRY, bull_put

MON, TUE, WED = date(2026, 10, 26), date(2026, 10, 27), date(2026, 10, 28)
STRIKES = range(22000, 28550, 50)


def _trade(
    forwards: dict[date, float],
    vols: dict[date, float] | None = None,
    fills: FillModel | None = None,
) -> tuple[ClosedTrade, InMemoryMarketData]:
    data = InMemoryMarketData(chain_history(forwards, EXPIRY, STRIKES, vols=vols))
    model = fills or SettleFill()
    days = list(forwards)
    ticket = Ticket(1, bull_put(short=24900, long=24700), 65, Decimal(0))
    opened = open_trade(ticket, days[0], data.option_bars(days[0]), model)
    closed = close_trade(opened, days[-1], data.option_bars(days[-1]), model, ["scripted"])
    return closed, data


def _check_sums(closed: ClosedTrade, a: PnlAttribution) -> None:
    assert a.net == closed.net_pnl
    assert a.costs == closed.trade.entry_costs + closed.exit_costs


def test_quiet_market_is_mostly_theta() -> None:
    closed, data = _trade(dict.fromkeys((MON, TUE, WED), FORWARD))
    a = attribute(closed, data)
    _check_sums(closed, a)
    assert a.execution == 0  # settle fills
    assert a.theta > 0  # short premium decays
    assert abs(a.delta) < Decimal(1)
    assert abs(a.vega) < Decimal(1)
    assert abs(a.residual) < a.theta * Decimal("0.2")


def test_fall_is_explained_by_delta_and_gamma() -> None:
    closed, data = _trade({MON: FORWARD, TUE: FORWARD - 150})
    a = attribute(closed, data)
    _check_sums(closed, a)
    assert a.delta < 0  # short put spread loses on a fall
    assert a.gamma < 0  # net short gamma
    explained = a.delta + a.gamma + a.theta + a.vega
    assert abs(a.residual) < abs(explained) * Decimal("0.2")


def test_vol_spike_is_explained_by_vega() -> None:
    closed, data = _trade({MON: FORWARD, TUE: FORWARD}, vols={TUE: VOL + 0.03})
    a = attribute(closed, data)
    _check_sums(closed, a)
    assert a.vega < 0  # short vega
    assert abs(a.residual) < abs(a.vega) * Decimal("0.2")


def test_realistic_fills_show_up_as_execution_cost() -> None:
    fills = BarFillModel(FillConfig(), ProportionalSpread())
    closed, data = _trade(dict.fromkeys((MON, TUE), FORWARD), fills=fills)
    a = attribute(closed, data)
    _check_sums(closed, a)
    assert a.execution < 0


def test_same_day_round_trip_has_no_greek_terms() -> None:
    closed, data = _trade({MON: FORWARD})
    a = attribute(closed, data)
    assert (a.delta, a.gamma, a.vega, a.theta, a.residual) == (Decimal(0),) * 5
    _check_sums(closed, a)


def test_leg_without_iv_goes_to_residual() -> None:
    closed, data = _trade({MON: FORWARD, TUE: FORWARD})
    spread = bull_put(short=24900, long=24700)
    tue = dict(data.option_bars(TUE))
    hedge = spread.long.contract
    tue[hedge] = replace(tue[hedge], settle=Decimal("0.01"))  # sub-tick: no IV
    patched = InMemoryMarketData([*data.option_bars(MON).values(), *tue.values()])
    reclosed = close_trade(closed.trade, TUE, patched.option_bars(TUE), SettleFill(), ["x"])
    a = attribute(reclosed, patched)
    _check_sums(reclosed, a)
    assert a.theta != attribute(closed, data).theta  # the hedge's theta is not counted


def test_missing_bar_fails_loudly() -> None:
    closed, data = _trade({MON: FORWARD, TUE: FORWARD})
    partial = InMemoryMarketData(
        [b for c, b in data.option_bars(TUE).items() if c != closed.trade.position.legs[0].contract]
        + list(data.option_bars(MON).values())
    )
    with pytest.raises(DataError):
        attribute(closed, partial)

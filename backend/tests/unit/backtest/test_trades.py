"""Shared trade pricing: marks use close when NSE reports no settle."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

from fintrade.backtest.data import chain_points
from fintrade.backtest.trades import Ticket, mark_pnl, open_trade
from tests.support.backtest import SettleFill, market, spread_bars
from tests.support.instruments import bull_put

MON, TUE = date(2026, 10, 26), date(2026, 10, 27)


def test_unreported_settle_marks_at_close_not_zero() -> None:
    spread = bull_put()
    data = market(spread_bars(spread, {MON: ("40", "10"), TUE: ("30", "8")}))
    trade = open_trade(Ticket(1, spread, 65, Decimal(0)), MON, data.option_bars(MON), SettleFill())
    tue = dict(data.option_bars(TUE))
    hedge = spread.long.contract
    tue[hedge] = replace(tue[hedge], settle=Decimal(0))  # close stays 8
    # short gains 10, hedge loses 2 (not 10): (10 - 2) x 130
    assert mark_pnl(trade, tue) == Decimal(1040)


def test_chain_points_use_the_mark() -> None:
    spread = bull_put()
    bars = dict(market(spread_bars(spread, {MON: ("40", "10")})).option_bars(MON))
    short = spread.short.contract
    bars[short] = replace(bars[short], settle=Decimal(0))
    assert chain_points(bars, spread.expiry)[short.strike].put == Decimal(40)

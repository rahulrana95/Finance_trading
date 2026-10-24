"""Where a closed trade's P&L came from: execution, delta, gamma, vega, theta, costs.

    net = execution + delta + gamma + vega + theta + residual - costs   (exactly)

- execution: fills versus settle on the entry and exit days (spread + slippage paid)
- delta / gamma / vega / theta: a second-order Taylor step per held day, per leg, using
  that day's chain Greeks (forward from parity, IV per strike from the OTM side)
- residual: whatever the Greeks do not explain (higher-order terms, smile moves, and
  legs whose price is too small for an IV, e.g. far hedges)
"""

import itertools
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from fintrade.backtest.data import DECISION_TIME, DEFAULT_RATE, DayBars, MarketData, chain_points
from fintrade.backtest.trades import ClosedTrade, leg_bar
from fintrade.core.instruments import Leg, Side
from fintrade.core.money import Rupees, round_rupees
from fintrade.core.pricing.black76 import time_to_expiry_years
from fintrade.core.pricing.chain import ChainGreeks, chain_greeks
from fintrade.core.timezone import IST

_VOL_POINT = 100.0  # vega is per 1 volatility point (0.01)
_MIN_PRICE = Decimal("0.05")  # one tick: below this no IV is trusted


@dataclass(frozen=True, slots=True)
class PnlAttribution:
    execution: Rupees
    delta: Rupees
    gamma: Rupees
    vega: Rupees
    theta: Rupees
    residual: Rupees
    costs: Rupees

    @property
    def net(self) -> Rupees:
        explained = self.execution + self.delta + self.gamma + self.vega + self.theta
        return explained + self.residual - self.costs


@dataclass(frozen=True, slots=True)
class _Snapshot:
    bars: DayBars
    chain: ChainGreeks
    when: datetime


def attribute(trade: ClosedTrade, data: MarketData, rate: float = DEFAULT_RATE) -> PnlAttribution:
    opened = trade.trade
    days = [d for d in data.trading_days() if opened.entry_day <= d <= trade.exit_day]
    snaps = [_snapshot(data.option_bars(d), opened.position.expiry, d, rate) for d in days]
    totals = {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0}
    for before, after in itertools.pairwise(snaps):
        for leg in opened.position.legs:
            for key, value in _step(leg, before, after).items():
                totals[key] += value * _units(leg, opened.lot_size)
    greek = {key: round_rupees(Decimal(value)) for key, value in totals.items()}
    execution = _execution(trade, snaps[0].bars, snaps[-1].bars)
    residual = trade.gross_pnl - execution - sum(greek.values(), start=Decimal(0))
    return PnlAttribution(
        execution=execution,
        residual=residual,
        costs=opened.entry_costs + trade.exit_costs,
        **greek,
    )


def _snapshot(bars: DayBars, expiry: date, day: date, rate: float) -> _Snapshot:
    when = datetime.combine(day, DECISION_TIME, tzinfo=IST)
    points = list(chain_points(bars, expiry).values())
    years = time_to_expiry_years(when, expiry)
    return _Snapshot(bars, chain_greeks(points, years, rate, _MIN_PRICE), when)


def _step(leg: Leg, before: _Snapshot, after: _Snapshot) -> Mapping[str, float]:
    """Per-unit Taylor terms for a long position in this leg's option over one step."""
    strike = leg.contract.strike
    start, end = before.chain.by_strike.get(strike), after.chain.by_strike.get(strike)
    if start is None or end is None:
        return {}  # no IV on one side: the whole move stays in the residual
    g = start.of(leg.contract.option_type)
    move = after.chain.forward - before.chain.forward
    days = (after.when - before.when).total_seconds() / 86_400
    return {
        "delta": g.delta * move,
        "gamma": 0.5 * g.gamma * move * move,
        "vega": g.vega_per_vol_point * (end.iv - start.iv) * _VOL_POINT,
        "theta": g.theta_per_day * days,
    }


def _units(leg: Leg, lot_size: int) -> int:
    sign = 1 if leg.side is Side.BUY else -1
    return sign * leg.lots * lot_size


def _execution(trade: ClosedTrade, entry_bars: DayBars, exit_bars: DayBars) -> Rupees:
    """Fill price versus settle on both days, signed so that paying the spread is negative."""
    total = Decimal(0)
    for leg in trade.trade.position.legs:
        units = _units(leg, trade.trade.lot_size)
        contract = leg.contract
        entry_gap = leg_bar(entry_bars, leg).settle - trade.trade.entry_prices[contract]
        exit_gap = trade.exit_prices[contract] - leg_bar(exit_bars, leg).settle
        total += (entry_gap + exit_gap) * units
    return total

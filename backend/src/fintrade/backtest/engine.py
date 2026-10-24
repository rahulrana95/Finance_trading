"""Daily replay engine. Calls the same core/ code the live system will use.

Per trading day, in order:
1. loss-limit status from history up to yesterday (core.risk.budget)
2. exits for every open trade (exit policy; loss limit hit forces exits)
3. at most one entry: next week's expiry (core.calendar), lot size must be known,
   and the proposal must pass every AGENTS.md hard limit (core.rules.entry) whatever
   the entry policy says
4. end-of-day equity recorded (charges paid count immediately)
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from fintrade.backtest.data import DayBars, GuardedMarketData, MarketData
from fintrade.core.bars import DailyContractBar
from fintrade.core.calendar import ExpiryCalendar
from fintrade.core.charges import order_charges
from fintrade.core.errors import DataError
from fintrade.core.instruments import Leg, OptionContract, Position, Side
from fintrade.core.limits import HARD_LIMITS
from fintrade.core.money import Rupees
from fintrade.core.pnl import Prices, mark_to_market, risk
from fintrade.core.risk.budget import DailyPnl, budget_status
from fintrade.core.rules.entry import AccountState, ProposedEntry, check_entry

_PCT = Decimal(100)
_ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class EntryProposal:
    position: Position
    short_deltas: Mapping[OptionContract, Decimal]
    margin_required: Rupees


class EntryPolicy(Protocol):
    def propose(self, day: date, bars: DayBars, expiry: date) -> EntryProposal | None: ...


class FillModel(Protocol):
    def fill(self, bar: DailyContractBar, order_side: Side) -> Rupees:
        """Price per unit for an order on `bar`: BUY pays, SELL receives."""
        ...


@dataclass(frozen=True, slots=True)
class OpenTrade:
    trade_id: int
    position: Position
    entry_day: date
    entry_prices: Prices
    lot_size: int
    margin: Rupees
    entry_costs: Rupees
    max_profit: Rupees
    max_loss: Rupees


class ExitPolicy(Protocol):
    def reasons(
        self, trade: OpenTrade, day: date, bars: DayBars, loss_limit_hit: bool
    ) -> list[str]: ...


@dataclass(frozen=True, slots=True)
class ClosedTrade:
    trade: OpenTrade
    exit_day: date
    exit_prices: Prices
    exit_costs: Rupees
    reasons: tuple[str, ...]
    gross_pnl: Rupees

    @property
    def net_pnl(self) -> Rupees:
        return self.gross_pnl - self.trade.entry_costs - self.exit_costs


class DecisionKind(StrEnum):
    OPENED = "opened"
    NO_ACTION = "no_action"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class Decision:
    day: date
    kind: DecisionKind
    details: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    capital: Rupees
    margin_available: Rupees


@dataclass
class BacktestResult:
    closed: list[ClosedTrade] = field(default_factory=list)
    still_open: list[OpenTrade] = field(default_factory=list)
    daily: list[DailyPnl] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Strategy:
    entry: EntryPolicy
    exit: ExitPolicy
    fills: FillModel


class ReplayEngine:
    def __init__(
        self,
        data: MarketData,
        strategy: Strategy,
        calendar: ExpiryCalendar,
        lot_sizes: Mapping[date, int | None],
        config: BacktestConfig,
    ) -> None:
        self._data = GuardedMarketData(data)
        self._strategy = strategy
        self._calendar = calendar
        self._lot_sizes = lot_sizes
        self._config = config
        self._open: list[OpenTrade] = []
        self._realized = _ZERO
        self._next_id = 1
        self._result = BacktestResult()

    def run(self, days: Sequence[date] | None = None) -> BacktestResult:
        for day in days if days is not None else self._data.trading_days():
            self._step(day)
        self._result.still_open = list(self._open)
        return self._result

    def _step(self, day: date) -> None:
        self._data.advance_to(day)
        bars = self._data.option_bars(day)
        limit_hit = self._loss_limit_hit()
        for trade in list(self._open):
            reasons = self._strategy.exit.reasons(trade, day, bars, limit_hit)
            if reasons:
                self._close(trade, day, bars, reasons)
        if limit_hit:
            self._decide(day, DecisionKind.BLOCKED, "loss limit hit")
        else:
            self._try_entry(day, bars)
        open_mtm = sum((self._open_value(t, bars) for t in self._open), start=_ZERO)
        self._result.daily.append(DailyPnl(day, self._realized, open_mtm))

    def _loss_limit_hit(self) -> bool:
        history = self._result.daily
        return bool(history) and budget_status(self._config.capital, history).any_limit_hit

    def _remaining_budget(self) -> Rupees:
        history = self._result.daily
        if history:
            return budget_status(self._config.capital, history).remaining_monthly_budget
        return self._config.capital * HARD_LIMITS.max_monthly_drawdown_pct / _PCT

    def _try_entry(self, day: date, bars: DayBars) -> None:
        expiry = self._calendar.entry_expiry(day)
        if expiry is None:
            self._decide(day, DecisionKind.NO_ACTION, "no entry expiry today")
            return
        proposal = self._strategy.entry.propose(day, bars, expiry)
        if proposal is None:
            self._decide(day, DecisionKind.NO_ACTION, "policy proposed nothing")
            return
        lot_size = self._lot_sizes.get(expiry)
        if lot_size is None:
            self._decide(day, DecisionKind.BLOCKED, f"lot size unknown for {expiry}")
            return
        self._open_if_allowed(day, bars, proposal, expiry, lot_size)

    def _open_if_allowed(
        self, day: date, bars: DayBars, proposal: EntryProposal, expiry: date, lot_size: int
    ) -> None:
        position = proposal.position
        fills = {leg.contract: self._fill(leg, leg.side, bars) for leg in position.legs}
        position_risk = risk(position, fills, lot_size)
        account = AccountState(
            open_positions=len(self._open),
            new_positions_today=0,
            open_max_loss=sum((t.max_loss for t in self._open), start=_ZERO),
            remaining_monthly_budget=self._remaining_budget(),
            margin_used=sum((t.margin for t in self._open), start=_ZERO),
            margin_available=self._config.margin_available,
            loss_limit_hit=False,
        )
        entry = ProposedEntry(
            position=position,
            short_deltas=proposal.short_deltas,
            max_loss=position_risk.max_loss,
            margin_required=proposal.margin_required,
            entry_expiry=expiry,
        )
        violations = check_entry(entry, account)
        if violations:
            self._decide(day, DecisionKind.BLOCKED, *(str(v) for v in violations))
            return
        costs = self._costs(position, fills, lot_size, day, opening=True)
        trade = OpenTrade(
            self._next_id,
            position,
            day,
            fills,
            lot_size,
            proposal.margin_required,
            costs,
            position_risk.max_profit,
            position_risk.max_loss,
        )
        self._next_id += 1
        self._open.append(trade)
        self._decide(day, DecisionKind.OPENED, f"trade {trade.trade_id} {position.structure}")

    def _close(self, trade: OpenTrade, day: date, bars: DayBars, reasons: list[str]) -> None:
        exits = {
            leg.contract: self._fill(leg, _opposite(leg.side), bars) for leg in trade.position.legs
        }
        gross = mark_to_market(trade.position, trade.entry_prices, exits, trade.lot_size)
        costs = self._costs(trade.position, exits, trade.lot_size, day, opening=False)
        closed = ClosedTrade(trade, day, exits, costs, tuple(reasons), gross)
        self._open.remove(trade)
        self._realized += closed.net_pnl
        self._result.closed.append(closed)

    def _open_value(self, trade: OpenTrade, bars: DayBars) -> Rupees:
        marks = {leg.contract: _bar(bars, leg).settle for leg in trade.position.legs}
        mtm = mark_to_market(trade.position, trade.entry_prices, marks, trade.lot_size)
        return mtm - trade.entry_costs

    def _fill(self, leg: Leg, order_side: Side, bars: DayBars) -> Rupees:
        return self._strategy.fills.fill(_bar(bars, leg), order_side)

    @staticmethod
    def _costs(position: Position, prices: Prices, lot: int, day: date, *, opening: bool) -> Rupees:
        total = _ZERO
        for leg in position.legs:
            side = leg.side if opening else _opposite(leg.side)
            total += order_charges(side, prices[leg.contract], leg.lots * lot, day).total
        return total

    def _decide(self, day: date, kind: DecisionKind, *details: str) -> None:
        self._result.decisions.append(Decision(day, kind, details))


def _opposite(side: Side) -> Side:
    return Side.SELL if side is Side.BUY else Side.BUY


def _bar(bars: DayBars, leg: Leg) -> DailyContractBar:
    bar = bars.get(leg.contract)
    if bar is None:
        raise DataError(f"no bar for open leg {leg.contract}")
    return bar

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
from fintrade.backtest.trades import (
    ClosedTrade,
    FillModel,
    OpenTrade,
    Ticket,
    close_trade,
    mark_pnl,
    open_trade,
)
from fintrade.core.calendar import ExpiryCalendar
from fintrade.core.instruments import OptionContract, Position
from fintrade.core.limits import HARD_LIMITS
from fintrade.core.money import Rupees
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


class ExitPolicy(Protocol):
    def reasons(
        self, trade: OpenTrade, day: date, bars: DayBars, loss_limit_hit: bool
    ) -> list[str]: ...


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
        open_mtm = sum((mark_pnl(t, bars) - t.entry_costs for t in self._open), start=_ZERO)
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
        ticket = Ticket(self._next_id, proposal.position, lot_size, proposal.margin_required)
        trade = open_trade(ticket, day, bars, self._strategy.fills)
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
            position=proposal.position,
            short_deltas=proposal.short_deltas,
            max_loss=trade.max_loss,
            margin_required=proposal.margin_required,
            entry_expiry=expiry,
        )
        violations = check_entry(entry, account)
        if violations:
            self._decide(day, DecisionKind.BLOCKED, *(str(v) for v in violations))
            return
        self._next_id += 1
        self._open.append(trade)
        self._decide(day, DecisionKind.OPENED, f"trade {trade.trade_id} {trade.position.structure}")

    def _close(self, trade: OpenTrade, day: date, bars: DayBars, reasons: list[str]) -> None:
        closed = close_trade(trade, day, bars, self._strategy.fills, reasons)
        self._open.remove(trade)
        self._realized += closed.net_pnl
        self._result.closed.append(closed)

    def _decide(self, day: date, kind: DecisionKind, *details: str) -> None:
        self._result.decisions.append(Decision(day, kind, details))

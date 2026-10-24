"""What every candidate would have earned if taken alone (labels for the bandit, RL.md).

Each distinct candidate position is opened at that day's fills and held until the exit
policy closes it. Account-level limits are ignored: an outcome answers "how good was
this choice on this day", not "could the account take it".

Outcomes use prices after the decision day by construction. They are labels, so a
decision on day D may only learn from outcomes that closed before D:
`CounterfactualRun.known_before(D)` is the only way to read them for training.
"""

import bisect
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from fintrade.backtest.candidates import Candidate, CandidateConfig, generate_candidates
from fintrade.backtest.data import MarketData
from fintrade.backtest.engine import ExitPolicy
from fintrade.backtest.trades import ClosedTrade, FillModel, Ticket, close_trade, open_trade
from fintrade.core.calendar import ExpiryCalendar
from fintrade.core.instruments import Position

_NO_MARGIN = Decimal(0)  # account-level margin does not apply to a lone counterfactual


@dataclass(frozen=True, slots=True)
class CandidateOutcome:
    decision_day: date
    candidate: Candidate
    result: ClosedTrade


@dataclass(frozen=True, slots=True)
class SkippedDay:
    day: date
    reason: str


@dataclass
class CounterfactualRun:
    outcomes: list[CandidateOutcome] = field(default_factory=list)
    unfinished: list[tuple[date, Candidate]] = field(default_factory=list)  # data ran out
    skipped: list[SkippedDay] = field(default_factory=list)

    def known_before(self, day: date) -> list[CandidateOutcome]:
        """Outcomes whose trade had closed before `day`: safe to learn from on `day`."""
        return [o for o in self.outcomes if o.result.exit_day < day]


@dataclass(frozen=True, slots=True)
class Simulation:
    data: MarketData
    calendar: ExpiryCalendar
    lot_sizes: Mapping[date, int | None]
    fills: FillModel
    exit: ExitPolicy
    candidates: CandidateConfig


def counterfactuals(sim: Simulation, days: Sequence[date] | None = None) -> CounterfactualRun:
    trading_days = list(sim.data.trading_days())
    run = CounterfactualRun()
    for day in days if days is not None else trading_days:
        _day(sim, trading_days, day, run)
    return run


def _day(sim: Simulation, trading_days: list[date], day: date, run: CounterfactualRun) -> None:
    expiry = sim.calendar.entry_expiry(day)
    if expiry is None:
        run.skipped.append(SkippedDay(day, "no entry expiry"))
        return
    lot_size = sim.lot_sizes.get(expiry)
    if lot_size is None:
        run.skipped.append(SkippedDay(day, f"lot size unknown for {expiry}"))
        return
    bars = sim.data.option_bars(day)
    later = trading_days[bisect.bisect_right(trading_days, day) :]
    results: dict[Position, ClosedTrade | None] = {}  # same strikes, same outcome
    for candidate in generate_candidates(day, bars, expiry, sim.candidates):
        if candidate.position not in results:
            results[candidate.position] = _hold(sim, candidate.position, day, later, lot_size)
        result = results[candidate.position]
        if result is None:
            run.unfinished.append((day, candidate))
        else:
            run.outcomes.append(CandidateOutcome(day, candidate, result))


def _hold(
    sim: Simulation, position: Position, day: date, later: list[date], lot_size: int
) -> ClosedTrade | None:
    ticket = Ticket(0, position, lot_size, _NO_MARGIN)
    trade = open_trade(ticket, day, sim.data.option_bars(day), sim.fills)
    for exit_day in later:
        bars = sim.data.option_bars(exit_day)
        reasons = sim.exit.reasons(trade, exit_day, bars, loss_limit_hit=False)
        if reasons:
            return close_trade(trade, exit_day, bars, sim.fills, reasons)
    return None

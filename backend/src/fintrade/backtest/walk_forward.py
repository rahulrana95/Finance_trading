"""Walk-forward parameter search over counterfactual outcomes (AGENTS.md section 5).

Rolling windows: choose the best arm on a training window, then score that arm on the
next, unseen test window. Only training outcomes whose trade CLOSED before the test window
starts are used, so no test-period price reaches the choice. The out-of-sample results
of all test windows together are the honest estimate; in-sample scores are reported next
to them to show how much the choice was overfit.

An arm is a candidate grid point (structure, target delta, width) plus a minimum-credit
filter and the exit config the counterfactuals were run with. Account-level limits and
overlapping trades are not modelled here; the chosen parameters are then replayed through
the engine (T4.6b).
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from fintrade.backtest.counterfactuals import CandidateOutcome, CounterfactualRun
from fintrade.core.errors import InvalidInputError
from fintrade.core.instruments import CreditSpread, Structure
from fintrade.core.pnl import credit_points

_PCT = Decimal(100)

type Scorer = Callable[[Sequence[CandidateOutcome]], Decimal]


@dataclass(frozen=True, slots=True, order=True)
class Arm:
    exit_label: str
    structure: Structure
    target_delta: Decimal
    width: Decimal
    min_credit_pct: Decimal  # of width, on every side


@dataclass(frozen=True, slots=True)
class Window:
    train_start: date
    test_start: date
    test_end: date  # exclusive


@dataclass(frozen=True, slots=True)
class WindowResult:
    window: Window
    arm: Arm | None  # None: no arm had enough training trades -> no trading
    train_score: Decimal | None
    test: tuple[CandidateOutcome, ...]


@dataclass(frozen=True, slots=True)
class SearchConfig:
    train_months: int = 12
    test_months: int = 3
    min_train_trades: int = 30
    min_credit_pcts: tuple[Decimal, ...] = (Decimal(0), Decimal(5), Decimal(10))

    def __post_init__(self) -> None:
        if self.train_months < 1 or self.test_months < 1 or self.min_train_trades < 1:
            raise InvalidInputError("train / test months and min trades must be >= 1")
        if not self.min_credit_pcts or any(not 0 <= p < _PCT for p in self.min_credit_pcts):
            raise InvalidInputError(f"min credit pcts must be in [0, 100): {self.min_credit_pcts}")


def mean_net_pnl(outcomes: Sequence[CandidateOutcome]) -> Decimal:
    """Default score: average net P&L per trade."""
    return sum((o.result.net_pnl for o in outcomes), start=Decimal(0)) / len(outcomes)


def add_months(day: date, months: int) -> date:
    """Same day-of-month `months` later, clamped to the 28th so it always exists."""
    index = day.year * 12 + day.month - 1 + months
    return date(index // 12, index % 12 + 1, min(day.day, 28))


def windows(start: date, end: date, config: SearchConfig) -> list[Window]:
    """Rolling windows whose test periods tile [start + train, end) without gaps."""
    found: list[Window] = []
    test_start = add_months(start, config.train_months)
    while test_start < end:
        test_end = min(add_months(test_start, config.test_months), end)
        train_start = add_months(test_start, -config.train_months)
        found.append(Window(train_start, test_start, test_end))
        test_start = test_end
    return found


def credit_pct_of_width(outcome: CandidateOutcome) -> Decimal:
    """Smallest side's credit as % of its width, at the simulated entry fills."""
    position = outcome.candidate.position
    sides = (
        (position,)
        if isinstance(position, CreditSpread)
        else (position.put_spread, position.call_spread)
    )
    prices = outcome.result.trade.entry_prices
    return min(credit_points(side, prices) / side.width * _PCT for side in sides)


def walk_forward(
    runs: Mapping[str, CounterfactualRun],
    start: date,
    end: date,
    config: SearchConfig,
    scorer: Scorer = mean_net_pnl,
) -> list[WindowResult]:
    """`runs` maps an exit-config label to the counterfactuals run with that config."""
    arms = _arms_with_outcomes(runs, config)
    return [_window(w, arms, config, scorer) for w in windows(start, end, config)]


def _arms_with_outcomes(
    runs: Mapping[str, CounterfactualRun], config: SearchConfig
) -> dict[Arm, list[CandidateOutcome]]:
    arms: dict[Arm, list[CandidateOutcome]] = {}
    for label, run in runs.items():
        for outcome in run.outcomes:
            c = outcome.candidate
            credit = credit_pct_of_width(outcome)
            for min_pct in config.min_credit_pcts:
                if credit >= min_pct:
                    arm = Arm(label, c.structure, c.target_delta, c.width, min_pct)
                    arms.setdefault(arm, []).append(outcome)
    return arms


def _window(
    window: Window,
    arms: Mapping[Arm, list[CandidateOutcome]],
    config: SearchConfig,
    scorer: Scorer,
) -> WindowResult:
    best: tuple[Decimal, Arm] | None = None
    for arm in sorted(arms):  # sorted: ties go to the same arm every run
        train = [
            o
            for o in arms[arm]
            if window.train_start <= o.decision_day and o.result.exit_day < window.test_start
        ]
        if len(train) < config.min_train_trades:
            continue
        score = scorer(train)
        if best is None or score > best[0]:
            best = (score, arm)
    if best is None:
        return WindowResult(window, None, None, ())
    score, arm = best
    test = tuple(o for o in arms[arm] if window.test_start <= o.decision_day < window.test_end)
    return WindowResult(window, arm, score, test)

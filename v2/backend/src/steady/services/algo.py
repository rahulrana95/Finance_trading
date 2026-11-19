"""Runs the algo: checks each approved stock, proposes ideas, and writes a readable log."""

import logging
import uuid
from collections.abc import Callable
from dataclasses import replace

from steady.clock import Clock
from steady.constants import (
    BUY_LEVELS_PCT,
    KIND_DRY_RUN,
    LEVEL_ACTION,
    LEVEL_ERROR,
    LEVEL_INFO,
    LEVEL_OK,
    LEVEL_WARN,
    RUN_DONE,
    RUN_FAILED,
    RUN_RUNNING,
    STATUS_APPROVED,
    SUMMARY_DRY_RUN,
    SUMMARY_FAILED,
    SUMMARY_INTERRUPTED,
    SUMMARY_NO_ACTION,
    SUMMARY_NO_PRICES,
    SUMMARY_RUNNING,
)
from steady.domain import Idea, Run, RunStep
from steady.ports import Store
from steady.services.ideas import build_idea
from steady.services.stocks import StockService, StockView

log = logging.getLogger(__name__)


class RunNotFoundError(Exception):
    """No run with that id."""


def _new_id() -> str:
    return uuid.uuid4().hex


class AlgoService:
    def __init__(
        self,
        stocks: StockService,
        store: Store,
        clock: Clock,
        new_id: Callable[[], str] = _new_id,
    ) -> None:
        self._stocks = stocks
        self._store = store
        self._clock = clock
        self._new_id = new_id

    # ---- reading ----
    def list_runs(self) -> list[Run]:
        return self._store.runs()

    def get_run(self, run_id: str) -> Run:
        run = self._store.run(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        return run

    def list_ideas(self) -> list[Idea]:
        return self._store.ideas()

    # ---- running ----
    def start(self, kind: str) -> tuple[Run, bool]:
        """Registers a run. If one is already running, returns that one and False."""
        with self._store.lock:
            running = next((r for r in self._store.runs() if r.status == RUN_RUNNING), None)
            if running is not None:
                return running, False
            run = Run(self._new_id(), kind, RUN_RUNNING, self._clock(), SUMMARY_RUNNING)
            self._store.add_run(run)
            return run, True

    def execute(self, run_id: str) -> Run:
        run = self.get_run(run_id)
        try:
            run.summary, run.status = self._check_stocks(run), RUN_DONE
        except Exception:  # a run must never take the scheduler or server down
            log.exception("algo run %s failed", run_id)
            self._step(run, "Run", LEVEL_ERROR, "Something went wrong. Nothing was proposed.")
            run.summary, run.status = SUMMARY_FAILED, RUN_FAILED
        if run.summary == SUMMARY_NO_PRICES:
            run.status = RUN_FAILED
        run.finished_at = self._clock()
        self._store.save_run(run)
        return run

    def recover(self) -> int:
        """After a restart nothing is running, so runs still marked running are closed."""
        stuck = [r for r in self._store.runs() if r.status == RUN_RUNNING]
        for run in stuck:
            run.status, run.summary, run.finished_at = (
                RUN_FAILED,
                SUMMARY_INTERRUPTED,
                self._clock(),
            )
            self._store.save_run(run)
        return len(stuck)

    def run(self, kind: str) -> Run:
        """Starts and finishes a run in one call. Joins nothing: a running one is left alone."""
        run, created = self.start(kind)
        return self.execute(run.id) if created else run

    # ---- the checks ----
    def _step(self, run: Run, subject: str, level: str, message: str) -> None:
        run.steps.append(RunStep(len(run.steps) + 1, self._clock(), subject, level, message))

    def _check_stocks(self, run: Run) -> str:
        views = self._stocks.list_stocks()
        priced = [v for v in views if v.price_as_of]
        if not priced:
            self._step(run, "Prices", LEVEL_ERROR, "The price source did not answer for any stock.")
            return SUMMARY_NO_PRICES
        self._step(
            run,
            "Prices",
            LEVEL_OK,
            f"Loaded for {len(priced)} of {len(views)} stocks: closes of "
            f"{priced[0].price_as_of} from {priced[0].price_source}.",
        )
        approved = [v for v in views if v.seed.status == STATUS_APPROVED]
        created = sum(self._check_one(run, view, len(approved)) for view in approved)
        others = [v.seed.name for v in views if v.seed.status != STATUS_APPROVED and v.zone > 0]
        if others:
            self._step(
                run,
                "Not approved",
                LEVEL_INFO,
                f"In a buy zone but not approved, so no idea: {', '.join(others)}.",
            )
        if run.kind == KIND_DRY_RUN:
            summary = SUMMARY_DRY_RUN
        elif created:
            summary = f"{created} idea{'' if created == 1 else 's'} proposed"
        else:
            summary = SUMMARY_NO_ACTION
        self._step(run, "Done", LEVEL_OK, f"{summary}.")
        return summary

    def _check_one(self, run: Run, view: StockView, approved_count: int) -> int:
        """Logs one stock and returns 1 if a new idea was created."""
        name = view.seed.name
        waiting = self._store.open_idea(view.seed.symbol)
        if not view.price_as_of:
            self._step(run, name, LEVEL_WARN, "No prices, so it was skipped.")
            return 0
        where = f"{view.below_high_pct}% below its 6-month high"
        if view.zone == 0:
            ended = ""
            if waiting is not None and run.kind != KIND_DRY_RUN:
                self._store.expire(waiting)
                ended = " The earlier idea has expired."
            self._step(
                run,
                name,
                LEVEL_INFO,
                f"{where}. First buy needs {BUY_LEVELS_PCT[0]:.0f}%. Nothing to do.{ended}",
            )
            return 0
        if run.kind == KIND_DRY_RUN:
            self._step(
                run,
                name,
                LEVEL_ACTION,
                f"{where}, in buy zone {view.zone}. A real run would propose a buy. "
                "Dry run: no idea created.",
            )
            return 0
        idea = build_idea(view, approved_count, self._new_id(), self._clock())
        if idea is None:  # pragma: no cover - a stock in a zone always has a reached step
            return 0
        if waiting is not None:
            self._store.save_idea(replace(idea, id=waiting.id, created_at=waiting.created_at))
            self._step(
                run,
                name,
                LEVEL_INFO,
                f"{where}, in buy zone {view.zone}. An idea is already waiting; "
                "its plan was refreshed.",
            )
            return 0
        self._store.save_idea(idea)
        self._step(
            run,
            name,
            LEVEL_ACTION,
            f"{where}, in buy zone {view.zone}. Proposed a {idea.plan.instrument_type} buy. "
            f"{idea.plan.futures_note}",
        )
        return 1

"""The algo run: what it checks, what it proposes and what it writes down."""

from datetime import UTC, datetime
from itertools import count

import pytest

from steady.adapters.memory import MemoryStore
from steady.adapters.seed import load_seed_stocks
from steady.constants import (
    IDEA_EXPIRED,
    IDEA_NEW,
    KIND_DRY_RUN,
    KIND_ON_DEMAND,
    KIND_SCHEDULED,
    LEVEL_ACTION,
    LEVEL_ERROR,
    LEVEL_WARN,
    RUN_DONE,
    RUN_FAILED,
    RUN_RUNNING,
    SUMMARY_DRY_RUN,
    SUMMARY_FAILED,
    SUMMARY_INTERRUPTED,
    SUMMARY_NO_ACTION,
    SUMMARY_NO_PRICES,
)
from steady.domain import Close
from steady.services.algo import AlgoService, RunNotFoundError
from steady.services.stocks import StockService
from tests.support import FakePrices, closes

NOW = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
SLIDE = closes([100.0] * 60 + [95.0, 90.0, 85.0])
FLAT = closes([100.0] * 63)
APPROVED = 5


def clock() -> datetime:
    return NOW


def make(
    default: list[Close] | None = SLIDE,
    data: dict[str, list[Close] | None] | None = None,
    store: MemoryStore | None = None,
) -> AlgoService:
    stocks = StockService(load_seed_stocks(), FakePrices(data, default), clock)
    ids = count(1)
    return AlgoService(stocks, store or MemoryStore(), clock, lambda: f"id{next(ids)}")


def messages(run, subject: str) -> list[str]:
    return [s.message for s in run.steps if s.subject == subject]


def test_a_run_proposes_one_idea_per_approved_stock_in_a_zone():
    algo = make()
    run = algo.run(KIND_ON_DEMAND)
    assert (run.status, run.summary, run.finished_at) == (RUN_DONE, "5 ideas proposed", NOW)
    ideas = algo.list_ideas()
    assert len(ideas) == APPROVED
    assert {i.status for i in ideas} == {IDEA_NEW}
    assert [s.seq for s in run.steps] == list(range(1, len(run.steps) + 1))
    assert messages(run, "Prices") == [
        "Loaded for 12 of 12 stocks: closes of 2026-11-17 from Fake prices."
    ]
    assert messages(run, "Titan") == [
        "15.0% below its 6-month high, in buy zone 1. Proposed a cash buy. "
        "Futures not offered: lot size needs data."
    ]
    assert "Coforge" in messages(run, "Not approved")[0]
    assert messages(run, "Done") == ["5 ideas proposed."]


def test_one_idea_is_said_in_the_singular():
    algo = make(default=FLAT, data={"TITAN": SLIDE})
    assert algo.run(KIND_SCHEDULED).summary == "1 idea proposed"


def test_nothing_in_a_zone_means_no_action():
    algo = make(default=FLAT)
    run = algo.run(KIND_ON_DEMAND)
    assert (run.status, run.summary) == (RUN_DONE, SUMMARY_NO_ACTION)
    assert algo.list_ideas() == []
    assert messages(run, "Titan") == [
        "0.0% below its 6-month high. First buy needs 10%. Nothing to do."
    ]
    assert messages(run, "Not approved") == []


def test_a_dry_run_explains_but_creates_nothing():
    algo = make()
    run = algo.run(KIND_DRY_RUN)
    assert run.summary == SUMMARY_DRY_RUN
    assert algo.list_ideas() == []
    step = next(s for s in run.steps if s.subject == "Titan")
    assert step.level == LEVEL_ACTION
    assert step.message.endswith("Dry run: no idea created.")


def test_a_second_run_refreshes_the_waiting_idea_instead_of_adding_one():
    algo = make()
    algo.run(KIND_ON_DEMAND)
    before = {i.symbol: i.id for i in algo.list_ideas()}
    run = algo.run(KIND_ON_DEMAND)
    assert run.summary == SUMMARY_NO_ACTION
    assert {i.symbol: i.id for i in algo.list_ideas()} == before
    assert "already waiting" in messages(run, "Titan")[0]


def test_an_idea_expires_when_the_stock_leaves_the_zone():
    store = MemoryStore()
    make(store=store).run(KIND_ON_DEMAND)
    recovered = make(default=FLAT, store=store)
    dry = recovered.run(KIND_DRY_RUN)
    assert {i.status for i in store.ideas()} == {IDEA_NEW}  # a dry run changes nothing
    assert "expired" not in messages(dry, "Titan")[0]
    run = recovered.run(KIND_ON_DEMAND)
    assert {i.status for i in store.ideas()} == {IDEA_EXPIRED}
    assert messages(run, "Titan")[0].endswith("The earlier idea has expired.")


def test_a_stock_without_prices_is_skipped_with_a_warning():
    algo = make(data={"TITAN": None})
    run = algo.run(KIND_ON_DEMAND)
    step = next(s for s in run.steps if s.subject == "Titan")
    assert (step.level, step.message) == (LEVEL_WARN, "No prices, so it was skipped.")
    assert run.summary == "4 ideas proposed"
    assert messages(run, "Prices")[0].startswith("Loaded for 11 of 12 stocks")


def test_no_prices_at_all_fails_the_run():
    algo = make(default=None)
    run = algo.run(KIND_ON_DEMAND)
    assert (run.status, run.summary) == (RUN_FAILED, SUMMARY_NO_PRICES)
    assert run.steps[-1].level == LEVEL_ERROR
    assert algo.list_ideas() == []


def test_an_unexpected_error_fails_the_run_and_is_logged(monkeypatch: pytest.MonkeyPatch):
    algo = make()

    def boom() -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(algo._stocks, "list_stocks", boom)
    run = algo.run(KIND_ON_DEMAND)
    assert (run.status, run.summary, run.finished_at) == (RUN_FAILED, SUMMARY_FAILED, NOW)
    assert run.steps[-1].message == "Something went wrong. Nothing was proposed."


def test_only_one_run_at_a_time():
    algo = make()
    first, created = algo.start(KIND_ON_DEMAND)
    assert (first.status, created) == (RUN_RUNNING, True)
    again, created_again = algo.start(KIND_DRY_RUN)
    assert (again.id, created_again) == (first.id, False)
    assert algo.run(KIND_SCHEDULED).status == RUN_RUNNING  # left alone, not run twice
    assert algo.execute(first.id).status == RUN_DONE
    assert algo.start(KIND_ON_DEMAND)[1] is True


def test_runs_are_listed_newest_first_and_read_by_id():
    algo = make()
    first = algo.run(KIND_ON_DEMAND)
    second = algo.run(KIND_DRY_RUN)
    assert [r.id for r in algo.list_runs()] == [second.id, first.id]
    assert algo.get_run(first.id) is first
    with pytest.raises(RunNotFoundError):
        algo.get_run("nope")


def test_ids_are_unique_by_default():
    stocks = StockService(load_seed_stocks(), FakePrices(default=FLAT), clock)
    algo = AlgoService(stocks, MemoryStore(), clock)
    assert algo.run(KIND_ON_DEMAND).id != algo.run(KIND_ON_DEMAND).id


def test_runs_left_running_by_a_restart_are_closed():
    store = MemoryStore()
    stuck, _ = make(store=store).start(KIND_ON_DEMAND)
    restarted = make(store=store)
    assert restarted.recover() == 1
    assert (stuck.status, stuck.summary, stuck.finished_at) == (
        RUN_FAILED,
        SUMMARY_INTERRUPTED,
        NOW,
    )
    assert restarted.recover() == 0
    assert restarted.start(KIND_ON_DEMAND)[1] is True

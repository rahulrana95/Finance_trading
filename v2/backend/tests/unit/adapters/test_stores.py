"""Both stores for runs and ideas (memory and database) must behave the same."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from steady.adapters.memory import MemoryStore
from steady.constants import IDEA_EXPIRED, IDEA_NEW, KIND_ON_DEMAND, RUN_DONE
from steady.core.plan import Plan, PlanStep
from steady.core.screen import Odds
from steady.db.engine import make_engine
from steady.db.models import Base
from steady.db.store import SqlStore
from steady.domain import Idea, Run, RunStep, Screen, ScreenRow
from steady.ports import Store

NOW = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)


def sql_store(max_runs: int) -> SqlStore:
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    return SqlStore(engine, max_runs)


@pytest.fixture(params=[MemoryStore, sql_store], ids=["memory", "database"])
def make(request: pytest.FixtureRequest):
    made: list[Store] = []

    def build(max_runs: int) -> Store:
        made.append(request.param(max_runs))
        return made[-1]

    yield build
    for store in made:
        store.close()


def run(run_id: str) -> Run:
    return Run(run_id, KIND_ON_DEMAND, RUN_DONE, NOW, "done")


def idea(idea_id: str, symbol: str, minutes: int = 0) -> Idea:
    plan = Plan(0, (), "cash", "")
    at = NOW + timedelta(minutes=minutes)
    return Idea(idea_id, symbol, symbol, 1, plan, 100.0, 60.0, 50, (), (), IDEA_NEW, at)


def test_runs_are_newest_first_and_found_by_id(make):
    store: Store = make(50)
    store.add_run(run("a"))
    store.add_run(run("b"))
    assert [r.id for r in store.runs()] == ["b", "a"]
    assert store.run("a") is not None
    assert store.run("zz") is None


def test_only_the_latest_runs_are_listed(make):
    store: Store = make(2)
    for run_id in "abc":
        store.add_run(run(run_id))
    assert [r.id for r in store.runs()] == ["c", "b"]


def test_ideas_are_newest_first_and_saving_again_replaces(make):
    store: Store = make(50)
    store.save_idea(idea("1", "TITAN"))
    store.save_idea(idea("2", "MARICO", minutes=5))
    store.save_idea(replace(idea("1", "TITAN"), zone=2))
    assert [(i.id, i.zone) for i in store.ideas()] == [("2", 1), ("1", 2)]


def test_an_expired_idea_is_no_longer_open(make):
    store: Store = make(50)
    first = idea("1", "TITAN")
    store.save_idea(first)
    assert store.open_idea("TITAN") == first  # also proves the full round trip
    assert store.open_idea("MARICO") is None
    store.expire(first)
    assert store.open_idea("TITAN") is None
    assert store.ideas()[0].status == IDEA_EXPIRED


def test_a_changed_run_is_saved_with_its_steps_and_times(make):
    store: Store = make(50)
    store.add_run(run("a"))
    changed = store.run("a")
    assert changed is not None
    changed.status, changed.summary, changed.finished_at = "failed", "No prices", NOW
    changed.steps.append(RunStep(1, NOW, "Prices", "error", "No answer"))
    store.save_run(changed)
    assert store.run("a") == changed
    assert store.runs() == [changed]


def test_an_idea_keeps_its_plan_reasons_and_risks(make):
    store: Store = make(50)
    plan = Plan(400_000, (PlanStep(1, 10.0, 90.0, 66_666, "cash", 740, True, False),), "cash", "n")
    full = replace(idea("1", "TITAN"), plan=plan, reasons=("fell",), risks=("gold", "debt"))
    store.save_idea(full)
    assert store.ideas() == [full]


def test_the_latest_screen_is_kept_whole(make):
    store: Store = make(50)
    assert store.latest_screen() is None
    odds = (Odds(25.0, True, 3, 66.7, 33.3, 66.7, 2, 50.0, 50.0, 50.0),)
    rows = (
        ScreenRow(
            "TITAN", "Titan", "Jewellery", 75.0, "2026-11-17", 100.0, 25.0, 25.0, 2, 1, 2, 6.5
        ),
    )
    first = Screen("s1", NOW, 500, 447, 12.0, True, odds, rows)
    second = Screen("s2", NOW + timedelta(days=1), 500, 440, 3.0, False, (), ())
    store.save_screen(first)
    assert store.latest_screen() == first
    store.save_screen(second)
    assert store.latest_screen() == second

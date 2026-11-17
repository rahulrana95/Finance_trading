"""The in-memory store for runs and ideas."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from steady.adapters.memory import MemoryStore
from steady.constants import IDEA_EXPIRED, IDEA_NEW, KIND_ON_DEMAND, RUN_DONE
from steady.core.plan import Plan
from steady.domain import Idea, Run

NOW = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)


def run(run_id: str) -> Run:
    return Run(run_id, KIND_ON_DEMAND, RUN_DONE, NOW, "done")


def idea(idea_id: str, symbol: str, minutes: int = 0) -> Idea:
    plan = Plan(0, (), "cash", "")
    at = NOW + timedelta(minutes=minutes)
    return Idea(idea_id, symbol, symbol, 1, plan, 100.0, 60.0, 50, (), (), IDEA_NEW, at)


def test_runs_are_newest_first_and_found_by_id():
    store = MemoryStore()
    store.add_run(run("a"))
    store.add_run(run("b"))
    assert [r.id for r in store.runs()] == ["b", "a"]
    assert store.run("a") is not None
    assert store.run("zz") is None


def test_only_the_latest_runs_are_kept():
    store = MemoryStore(max_runs=2)
    for run_id in "abc":
        store.add_run(run(run_id))
    assert [r.id for r in store.runs()] == ["c", "b"]


def test_ideas_are_newest_first_and_saving_again_replaces():
    store = MemoryStore()
    store.save_idea(idea("1", "TITAN"))
    store.save_idea(idea("2", "MARICO", minutes=5))
    store.save_idea(replace(idea("1", "TITAN"), zone=2))
    assert [(i.id, i.zone) for i in store.ideas()] == [("2", 1), ("1", 2)]


def test_an_expired_idea_is_no_longer_open():
    store = MemoryStore()
    first = idea("1", "TITAN")
    store.save_idea(first)
    assert store.open_idea("TITAN") == first
    assert store.open_idea("MARICO") is None
    store.expire(first)
    assert store.open_idea("TITAN") is None
    assert store.ideas()[0].status == IDEA_EXPIRED

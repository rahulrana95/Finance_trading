"""With a database, runs and ideas survive a restart of the service."""

from pathlib import Path

from steady.constants import RUN_FAILED, SUMMARY_INTERRUPTED
from tests.conftest import ClientFactory


def test_runs_and_ideas_are_still_there_after_a_restart(make_client: ClientFactory, tmp_path: Path):
    url = f"sqlite:///{tmp_path / 'steady.db'}"
    first = make_client(None, database_url=url)
    run_id = first.post("/api/runs").json()["id"]
    ideas = first.get("/api/recommendations").json()
    assert len(ideas) == 5

    restarted = make_client(None, database_url=url)
    assert restarted.get(f"/api/runs/{run_id}").json()["summary"] == "5 ideas proposed"
    assert restarted.get("/api/recommendations").json() == ideas
    assert restarted.post("/api/runs").status_code == 202
    assert [r["summary"] for r in restarted.get("/api/runs").json()] == [
        "No action",
        "5 ideas proposed",
    ]


def test_a_run_cut_off_by_a_restart_is_closed(make_client: ClientFactory, tmp_path: Path):
    url = f"sqlite:///{tmp_path / 'steady.db'}"
    going, _ = make_client(None, database_url=url).app.state.algo.start("on_demand")  # type: ignore[attr-defined]
    body = make_client(None, database_url=url).get(f"/api/runs/{going.id}").json()
    assert (body["status"], body["summary"]) == (RUN_FAILED, SUMMARY_INTERRUPTED)

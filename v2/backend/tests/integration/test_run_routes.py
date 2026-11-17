"""Algo runs over HTTP: start one, watch it finish, read the ideas it proposed."""

import time

from steady.constants import KIND_SCHEDULED, RUN_DONE, RUN_RUNNING
from tests.conftest import ClientFactory

RUN_KEYS = {"id", "kind", "status", "startedAt", "finishedAt", "summary", "steps"}
IDEA_KEYS = {
    "id", "symbol", "name", "zone", "instrumentType", "steps", "targetPrice", "hardExitPrice",
    "evidenceScore", "reasons", "risks", "futuresNote", "status", "createdAt",
}  # fmt: skip
STEP_KEYS = {
    "step", "levelPct", "levelPrice", "amount", "instrument", "quantity", "reached", "filled"
}  # fmt: skip


def test_starting_a_run_answers_at_once_and_finishes_in_the_background(make_client: ClientFactory):
    client = make_client(None)
    started = client.post("/api/runs", json={"kind": "on_demand"})
    assert started.status_code == 202
    body = started.json()
    assert set(body) == RUN_KEYS
    assert (body["status"], body["kind"], body["finishedAt"]) == (RUN_RUNNING, "on_demand", None)
    finished = client.get(f"/api/runs/{body['id']}").json()
    assert (finished["status"], finished["summary"]) == (RUN_DONE, "5 ideas proposed")
    assert set(finished["steps"][0]) == {"seq", "at", "subject", "level", "message"}
    assert [r["id"] for r in client.get("/api/runs").json()] == [body["id"]]


def test_a_run_without_a_body_is_on_demand(make_client: ClientFactory):
    assert make_client(None).post("/api/runs").json()["kind"] == "on_demand"


def test_a_dry_run_creates_no_ideas(make_client: ClientFactory):
    client = make_client(None)
    assert client.post("/api/runs", json={"kind": "dry_run"}).status_code == 202
    assert client.get("/api/recommendations").json() == []


def test_only_on_demand_and_dry_runs_can_be_asked_for(make_client: ClientFactory):
    client = make_client(None)
    for kind in ("scheduled", "screener", ""):
        assert client.post("/api/runs", json={"kind": kind}).status_code == 422
    assert client.get("/api/runs").json() == []


def test_asking_while_a_run_is_going_returns_that_run(make_client: ClientFactory):
    client = make_client(None)
    going, _ = client.app.state.algo.start("on_demand")  # type: ignore[attr-defined]
    answer = client.post("/api/runs", json={"kind": "dry_run"}).json()
    assert (answer["id"], answer["kind"]) == (going.id, "on_demand")
    assert client.get(f"/api/runs/{going.id}").json()["status"] == RUN_RUNNING
    assert len(client.get("/api/runs").json()) == 1


def test_an_unknown_run_is_404(make_client: ClientFactory):
    response = make_client(None).get("/api/runs/nope")
    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown run nope"}


def test_ideas_have_the_shape_the_interface_expects(make_client: ClientFactory):
    client = make_client(None)
    client.post("/api/runs")
    ideas = client.get("/api/recommendations").json()
    assert len(ideas) == 5
    assert set(ideas[0]) == IDEA_KEYS
    assert set(ideas[0]["steps"][0]) == STEP_KEYS
    assert [s["amount"] for s in ideas[0]["steps"]] == [66666, 133333, 200000]


def test_ideas_can_be_filtered(make_client: ClientFactory):
    client = make_client(None)
    client.post("/api/runs")

    def count(query: str) -> int:
        return len(client.get(f"/api/recommendations?{query}").json())

    assert count("status=new&instrumentType=cash&minZone=1&minScore=1") == 5
    assert count("instrumentType=future") == 0
    assert count("status=expired") == 0
    assert count("minZone=2") == 0
    assert count("minScore=101") == 0
    assert client.get("/api/recommendations?minZone=deep").status_code == 422


def test_ideas_cannot_be_changed_yet(make_client: ClientFactory):
    client = make_client(None)
    assert client.post("/api/recommendations/x/approve").status_code == 404
    assert client.delete("/api/runs/x").status_code == 404


def test_with_the_scheduler_on_a_run_happens_at_start(make_client: ClientFactory):
    with make_client(None, scheduler=True) as client:
        deadline = time.monotonic() + 5
        runs: list[dict[str, str]] = []
        while time.monotonic() < deadline:
            runs = client.get("/api/runs").json()
            if runs and runs[0]["status"] == RUN_DONE:
                break
            time.sleep(0.02)
        assert [r["kind"] for r in runs] == [KIND_SCHEDULED]


def test_without_the_scheduler_nothing_runs_by_itself(make_client: ClientFactory):
    with make_client(None) as client:
        assert client.get("/api/runs").json() == []

"""Turns runs and ideas into table rows and back."""

from dataclasses import asdict
from datetime import datetime
from typing import Any

from steady.core.plan import Plan, PlanStep
from steady.core.screen import Odds
from steady.db.models import IdeaRow, RunRow, ScreenRecord
from steady.domain import Idea, Run, RunStep, Screen, ScreenRow

RUN_COLUMNS = ("kind", "status", "started_at", "finished_at", "summary")
IDEA_COLUMNS = ("id", "symbol", "status", "created_at")


def run_values(run: Run) -> dict[str, Any]:
    steps = [{**asdict(step), "at": step.at.isoformat()} for step in run.steps]
    return {**{name: getattr(run, name) for name in RUN_COLUMNS}, "steps": steps}


def to_run(row: RunRow) -> Run:
    steps = [RunStep(**{**step, "at": datetime.fromisoformat(step["at"])}) for step in row.steps]
    return Run(id=row.id, steps=steps, **{name: getattr(row, name) for name in RUN_COLUMNS})


def idea_values(idea: Idea) -> dict[str, Any]:
    fields = asdict(idea)
    columns = {name: fields.pop(name) for name in IDEA_COLUMNS}
    return {**columns, "body": fields}


def to_idea(row: IdeaRow) -> Idea:
    body = dict(row.body)
    plan = body.pop("plan")
    steps = tuple(PlanStep(**step) for step in plan.pop("steps"))
    return Idea(
        id=row.id,
        symbol=row.symbol,
        status=row.status,
        created_at=row.created_at,
        plan=Plan(steps=steps, **plan),
        reasons=tuple(body.pop("reasons")),
        risks=tuple(body.pop("risks")),
        **body,
    )


def screen_values(screen: Screen) -> dict[str, Any]:
    body = asdict(screen)
    return {"id": body.pop("id"), "created_at": body.pop("created_at"), "body": body}


def to_screen(row: ScreenRecord) -> Screen:
    body = dict(row.body)
    odds = tuple(Odds(**o) for o in body.pop("odds"))
    rows = tuple(ScreenRow(**r) for r in body.pop("rows"))
    return Screen(id=row.id, created_at=row.created_at, odds=odds, rows=rows, **body)

"""Ideas the algo proposed. Read-only: approving needs sign-in and a database first."""

from dataclasses import asdict

from fastapi import APIRouter

from steady.api.schemas import IdeaOut
from steady.constants import IDEAS_PATH
from steady.domain import Idea
from steady.services.algo import AlgoService
from steady.services.ideas import filter_ideas


def to_out(idea: Idea) -> IdeaOut:
    fields = asdict(idea)
    plan = fields.pop("plan")
    return IdeaOut.model_validate({**fields, **plan})


def ideas_router(algo: AlgoService) -> APIRouter:
    router = APIRouter(prefix=IDEAS_PATH, tags=["ideas"])

    @router.get("")
    def list_ideas(
        instrumentType: str | None = None,  # noqa: N803 - the interface sends camelCase
        status: str | None = None,
        minZone: int = 0,  # noqa: N803
        minScore: int = 0,  # noqa: N803
    ) -> list[IdeaOut]:
        ideas = filter_ideas(algo.list_ideas(), instrumentType, status, minZone, minScore)
        return [to_out(idea) for idea in ideas]

    return router

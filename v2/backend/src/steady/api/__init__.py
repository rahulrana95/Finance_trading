"""The JSON API. Each feature adds its router here."""

from fastapi import APIRouter, HTTPException, status

from steady.api.health import health_router
from steady.clock import Clock
from steady.config import Settings
from steady.constants import ALL_METHODS, API_PREFIX, MSG_NOT_FOUND


def api_router(settings: Settings, clock: Clock) -> APIRouter:
    router = APIRouter(prefix=API_PREFIX)
    router.include_router(health_router(settings, clock))

    @router.api_route("/{rest:path}", methods=ALL_METHODS, include_in_schema=False)
    def unknown(rest: str) -> None:
        # Without this, an unknown API address would fall through to the interface.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_NOT_FOUND)

    return router

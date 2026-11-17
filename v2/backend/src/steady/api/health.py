"""Liveness route."""

from fastapi import APIRouter

from steady.api.schemas import Health
from steady.clock import Clock
from steady.config import Settings
from steady.constants import HEALTH_PATH, SERVICE_NAME, STATUS_OK


def health_router(settings: Settings, clock: Clock) -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get(HEALTH_PATH)
    def health() -> Health:
        return Health(
            status=STATUS_OK, service=SERVICE_NAME, version=settings.version, time=clock()
        )

    return router

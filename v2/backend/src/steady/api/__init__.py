"""The JSON API. Each feature adds its router here."""

from fastapi import APIRouter, HTTPException, status

from steady.api.health import health_router
from steady.api.ideas import ideas_router
from steady.api.runs import runs_router
from steady.api.screens import screens_router
from steady.api.stocks import stocks_router
from steady.clock import Clock
from steady.config import Settings
from steady.constants import ALL_METHODS, API_PREFIX, MSG_NOT_FOUND
from steady.services.algo import AlgoService
from steady.services.screener import ScreenerService
from steady.services.stocks import StockService


def api_router(
    settings: Settings,
    clock: Clock,
    stocks: StockService,
    algo: AlgoService,
    screener: ScreenerService,
) -> APIRouter:
    router = APIRouter(prefix=API_PREFIX)
    router.include_router(health_router(settings, clock))
    router.include_router(stocks_router(stocks))
    router.include_router(runs_router(algo))
    router.include_router(ideas_router(algo))
    router.include_router(screens_router(screener))

    @router.api_route("/{rest:path}", methods=ALL_METHODS, include_in_schema=False)
    def unknown(rest: str) -> None:
        # Without this, an unknown API address would fall through to the interface.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_NOT_FOUND)

    return router

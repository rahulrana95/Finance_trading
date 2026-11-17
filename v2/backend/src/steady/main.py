"""Builds the Steady service: JSON API under /api, the built interface everywhere else."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from steady.adapters.memory import MemoryStore
from steady.adapters.seed import load_seed_stocks
from steady.adapters.yahoo import YahooPriceSource, new_client
from steady.api import api_router
from steady.clock import Clock, utc_now
from steady.config import Settings
from steady.constants import DOCS_PATH, OPENAPI_PATH, SERVICE_NAME
from steady.middleware import add_middleware
from steady.ports import PriceSource
from steady.scheduler import build_scheduler
from steady.services.algo import AlgoService
from steady.services.stocks import StockService
from steady.web.spa import mount_interface


def create_app(
    settings: Settings, clock: Clock = utc_now, prices: PriceSource | None = None
) -> FastAPI:
    source = prices or YahooPriceSource(new_client(), clock)
    stocks = StockService(load_seed_stocks(), source, clock)
    algo = AlgoService(stocks, MemoryStore(), clock)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        scheduler = build_scheduler(algo, clock) if settings.scheduler else None
        if scheduler:
            scheduler.start()
        yield
        if scheduler:
            scheduler.shutdown(wait=False)

    app = FastAPI(
        title=SERVICE_NAME.title(),
        version=settings.version,
        docs_url=DOCS_PATH,
        openapi_url=OPENAPI_PATH,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.algo = algo
    add_middleware(app)
    app.include_router(api_router(settings, clock, stocks, algo))
    mount_interface(app, settings.static_dir)  # last: it answers every remaining address
    return app


app = create_app(Settings())

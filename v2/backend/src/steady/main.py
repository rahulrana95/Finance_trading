"""Builds the Steady service: JSON API under /api, the built interface everywhere else."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from steady.adapters.memory import MemoryStore
from steady.adapters.seed import load_seed_stocks, load_universe
from steady.adapters.yahoo import YahooPriceSource, new_client
from steady.api import api_router
from steady.clock import Clock, utc_now
from steady.config import Settings
from steady.constants import DOCS_PATH, OPENAPI_PATH, SERVICE_NAME
from steady.db.engine import make_engine
from steady.db.migrate import upgrade
from steady.db.store import SqlStore
from steady.middleware import add_middleware
from steady.ports import PriceSource, Store
from steady.scheduler import build_scheduler
from steady.services.algo import AlgoService
from steady.services.screener import ScreenerService
from steady.services.stocks import StockService
from steady.web.spa import mount_interface


def make_store(settings: Settings) -> Store:
    if settings.database_url is None:
        return MemoryStore()
    url = settings.database_url.get_secret_value()
    upgrade(url)
    return SqlStore(make_engine(url))


def create_app(
    settings: Settings, clock: Clock = utc_now, prices: PriceSource | None = None
) -> FastAPI:
    source = prices or YahooPriceSource(new_client(), clock)
    stocks = StockService(load_seed_stocks(), source, clock)
    store = make_store(settings)
    algo = AlgoService(stocks, store, clock)
    algo.recover()
    screener = ScreenerService(load_universe(), source, store, clock)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        scheduler = build_scheduler(algo, screener, clock) if settings.scheduler else None
        if scheduler:
            scheduler.start()
        yield
        if scheduler:
            scheduler.shutdown(wait=False)
        store.close()

    app = FastAPI(
        title=SERVICE_NAME.title(),
        version=settings.version,
        docs_url=DOCS_PATH,
        openapi_url=OPENAPI_PATH,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.algo, app.state.store, app.state.screener = algo, store, screener
    add_middleware(app)
    app.include_router(api_router(settings, clock, stocks, algo, screener))
    mount_interface(app, settings.static_dir)  # last: it answers every remaining address
    return app


app = create_app(Settings())

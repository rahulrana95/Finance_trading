"""Builds the Steady service: JSON API under /api, the built interface everywhere else."""

from fastapi import FastAPI

from steady.adapters.seed import load_seed_stocks
from steady.adapters.yahoo import YahooPriceSource, new_client
from steady.api import api_router
from steady.clock import Clock, utc_now
from steady.config import Settings
from steady.constants import DOCS_PATH, OPENAPI_PATH, SERVICE_NAME
from steady.middleware import add_middleware
from steady.ports import PriceSource
from steady.services.stocks import StockService
from steady.web.spa import mount_interface


def create_app(
    settings: Settings, clock: Clock = utc_now, prices: PriceSource | None = None
) -> FastAPI:
    app = FastAPI(
        title=SERVICE_NAME.title(),
        version=settings.version,
        docs_url=DOCS_PATH,
        openapi_url=OPENAPI_PATH,
        redoc_url=None,
    )
    add_middleware(app)
    source = prices or YahooPriceSource(new_client(), clock)
    stocks = StockService(load_seed_stocks(), source, clock)
    app.include_router(api_router(settings, clock, stocks))
    mount_interface(app, settings.static_dir)  # last: it answers every remaining address
    return app


app = create_app(Settings())

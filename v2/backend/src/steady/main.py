"""Builds the Steady service: JSON API under /api, the built interface everywhere else."""

from fastapi import FastAPI

from steady.api import api_router
from steady.clock import Clock, utc_now
from steady.config import Settings
from steady.constants import DOCS_PATH, OPENAPI_PATH, SERVICE_NAME
from steady.middleware import add_middleware
from steady.web.spa import mount_interface


def create_app(settings: Settings, clock: Clock = utc_now) -> FastAPI:
    app = FastAPI(
        title=SERVICE_NAME.title(),
        version=settings.version,
        docs_url=DOCS_PATH,
        openapi_url=OPENAPI_PATH,
        redoc_url=None,
    )
    add_middleware(app)
    app.include_router(api_router(settings, clock))
    mount_interface(app, settings.static_dir)  # last: it answers every remaining address
    return app


app = create_app(Settings())

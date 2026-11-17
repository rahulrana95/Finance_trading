"""Middleware for every request, from standard packages."""

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware

from steady.constants import GZIP_MINIMUM_BYTES


def add_middleware(app: FastAPI) -> None:
    app.add_middleware(GZipMiddleware, minimum_size=GZIP_MINIMUM_BYTES)
    # Gives every request an X-Request-ID (kept if the caller sent one) for tracing in logs.
    app.add_middleware(CorrelationIdMiddleware)

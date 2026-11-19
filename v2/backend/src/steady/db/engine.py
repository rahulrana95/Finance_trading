"""The database connection."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool

from steady.constants import POSTGRES_DRIVER_PREFIX, POSTGRES_PREFIXES, SQLITE_PREFIX


def normalise_url(url: str) -> str:
    """Hosts hand out postgres:// addresses; SQLAlchemy needs the driver named."""
    for prefix in POSTGRES_PREFIXES:
        if url.startswith(prefix):
            return POSTGRES_DRIVER_PREFIX + url[len(prefix) :]
    return url


def make_engine(url: str) -> Engine:
    url = normalise_url(url)
    if url.startswith(SQLITE_PREFIX):  # tests only: one shared connection, any thread
        return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    return create_engine(url, pool_pre_ping=True)

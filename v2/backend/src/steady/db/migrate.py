"""Brings the database tables up to date. Runs when the service starts."""

from pathlib import Path

from alembic import command
from alembic.config import Config

from steady.db.engine import normalise_url

MIGRATIONS = Path(__file__).parent / "migrations"
HEAD = "head"
BASE = "base"


def _config(url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.set_main_option("sqlalchemy.url", normalise_url(url).replace("%", "%%"))
    return config


def upgrade(url: str) -> None:
    command.upgrade(_config(url), HEAD)


def downgrade(url: str) -> None:
    command.downgrade(_config(url), BASE)

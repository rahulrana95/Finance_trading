"""Alembic entry point. The address comes from steady.db.migrate, never from a file."""

from alembic import context
from sqlalchemy import create_engine

from steady.db.models import Base

engine = create_engine(context.config.get_main_option("sqlalchemy.url") or "")
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()

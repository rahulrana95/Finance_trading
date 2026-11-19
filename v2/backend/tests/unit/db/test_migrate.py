"""Migrations must build exactly the tables the models describe."""

from pathlib import Path

from sqlalchemy import create_engine, inspect

from steady.db.migrate import downgrade, upgrade
from steady.db.models import Base


def test_migrations_match_the_models_and_can_be_undone(tmp_path: Path):
    url = f"sqlite:///{tmp_path / 'steady.db'}"
    upgrade(url)
    upgrade(url)  # running again changes nothing
    engine = create_engine(url)
    found = inspect(engine)
    for table in Base.metadata.sorted_tables:
        columns = {c["name"]: c["nullable"] for c in found.get_columns(table.name)}
        assert columns == {c.name: c.nullable for c in table.columns}, table.name
        indexed = {tuple(i["column_names"]) for i in found.get_indexes(table.name)}
        assert {(c.name,) for c in table.columns if c.index} <= indexed, table.name
    downgrade(url)
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()

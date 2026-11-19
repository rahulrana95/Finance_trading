"""Database addresses and connections."""

import pytest

from steady.db.engine import make_engine, normalise_url


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgres://u:p@h:5432/d", "postgresql+psycopg://u:p@h:5432/d"),
        ("postgresql://u:p@h:5432/d", "postgresql+psycopg://u:p@h:5432/d"),
        ("postgresql+psycopg://u:p@h/d", "postgresql+psycopg://u:p@h/d"),
        ("sqlite://", "sqlite://"),
    ],
)
def test_the_driver_is_named(given: str, expected: str):
    assert normalise_url(given) == expected


def test_a_postgres_engine_is_built_without_connecting():
    engine = make_engine("postgres://u:p@localhost:1/d")
    assert (engine.dialect.name, engine.driver) == ("postgresql", "psycopg")
    assert "p" not in repr(engine.url).split("@")[0].split(":")[-1]  # password is masked


def test_a_test_engine_shares_one_connection():
    engine = make_engine("sqlite://")
    with engine.connect() as one, engine.connect() as two:
        assert one.connection.dbapi_connection is two.connection.dbapi_connection
    engine.dispose()

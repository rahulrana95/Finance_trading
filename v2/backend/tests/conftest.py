"""Shared fixtures: a fixed clock, a built-interface folder, and a client factory."""

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from steady.config import Settings
from steady.main import create_app
from tests.support import FakePrices, closes

FIXED_NOW = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
TEST_VERSION = "1.2.3"
INDEX_BODY = "<html>steady interface</html>"

ClientFactory = Callable[..., TestClient]
# 60 flat days, then a slide to 15% below the high: one open fall, buy zone 1.
SLIDE = closes([100.0] * 60 + [95.0, 90.0, 85.0])


@pytest.fixture
def static_dir(tmp_path: Path) -> Path:
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text(INDEX_BODY)
    (root / "assets" / "app.js").write_text("console.log('app')" + " " * 2000)
    (root / "favicon.svg").write_text("<svg/>")
    (tmp_path / "secret.txt").write_text("do not serve")
    return root


@pytest.fixture
def make_client() -> Iterator[ClientFactory]:
    clients: list[TestClient] = []

    def make(
        static: Path | None,
        prices: FakePrices | None = None,
        scheduler: bool = False,
        database_url: str | None = None,
    ) -> TestClient:
        settings = Settings(
            static_dir=static,
            version=TEST_VERSION,
            scheduler=scheduler,
            database_url=SecretStr(database_url) if database_url else None,
        )
        source = prices or FakePrices(default=SLIDE)
        clients.append(TestClient(create_app(settings, clock=lambda: FIXED_NOW, prices=source)))
        return clients[-1]

    yield make
    for client in clients:
        client.app.state.store.close()  # type: ignore[attr-defined]

"""Shared fixtures: a fixed clock, a built-interface folder, and a client factory."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from steady.config import Settings
from steady.main import create_app

FIXED_NOW = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
TEST_VERSION = "1.2.3"
INDEX_BODY = "<html>steady interface</html>"

ClientFactory = Callable[[Path | None], TestClient]


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
def make_client() -> ClientFactory:
    def make(static: Path | None) -> TestClient:
        settings = Settings(static_dir=static, version=TEST_VERSION)
        return TestClient(create_app(settings, clock=lambda: FIXED_NOW))

    return make

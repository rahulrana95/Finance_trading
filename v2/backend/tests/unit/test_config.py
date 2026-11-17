"""Settings come from STEADY_* variables and reject a folder that is not a built interface."""

from pathlib import Path

import pytest

from steady.config import Settings
from steady.constants import DEFAULT_VERSION


def test_defaults_to_api_only_and_a_dev_version(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("STEADY_STATIC_DIR", raising=False)
    monkeypatch.delenv("STEADY_VERSION", raising=False)
    settings = Settings()
    assert settings.static_dir is None
    assert settings.version == DEFAULT_VERSION


def test_reads_the_environment(monkeypatch: pytest.MonkeyPatch, static_dir: Path):
    monkeypatch.setenv("STEADY_STATIC_DIR", str(static_dir))
    monkeypatch.setenv("STEADY_VERSION", "9.9.9")
    settings = Settings()
    assert settings.static_dir == static_dir
    assert settings.version == "9.9.9"


def test_ignores_a_folder_without_an_index(tmp_path: Path):
    assert Settings(static_dir=tmp_path).static_dir is None


def test_is_read_only():
    with pytest.raises(ValueError, match="frozen"):
        Settings().version = "changed"

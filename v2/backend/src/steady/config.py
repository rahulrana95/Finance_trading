"""Service settings, read from STEADY_* environment variables."""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from steady.constants import DEFAULT_VERSION, ENV_PREFIX, INDEX_FILE


class Settings(BaseSettings):
    """What the service needs to start."""

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, frozen=True)

    static_dir: Path | None = None
    version: str = DEFAULT_VERSION
    scheduler: bool = False  # run the algo by itself during market hours

    @field_validator("static_dir")
    @classmethod
    def _only_a_built_interface(cls, value: Path | None) -> Path | None:
        # A folder without index.html is not a built interface; run as API only.
        if value is not None and not (value / INDEX_FILE).is_file():
            return None
        return value

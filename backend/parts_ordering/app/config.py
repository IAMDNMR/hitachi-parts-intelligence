"""
Settings, read from the environment rather than hardcoded.

The database URL defaults to a local SQLite file so the service runs with no
setup — clone, install, run. It is a real SQLAlchemy URL, so the only change
needed to point this at Postgres later is DATABASE_URL itself; nothing in the
models or the migrations is SQLite-specific.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./parts_ordering.db"

    # The Vite dev server's own origin. A comma-separated list, so a
    # deployed frontend's origin can be added later without code changes.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

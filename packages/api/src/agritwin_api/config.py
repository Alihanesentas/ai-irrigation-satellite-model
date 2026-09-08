"""Central secrets/configuration abstraction layer.

Same rationale and pattern as `agritwin_etl.config.Settings` (see that
module's docstring): nowhere else in agritwin_api should call `os.getenv`
directly or read credential material off disk without going through this
module. That keeps a future migration (e.g. SQLite -> Postgres, or a
PEM-on-disk signing key -> a secrets manager / Docker secret) to a single
file.

Two secrets live behind `Settings` here:

- `admin_api_key` — the bearer token required for `/admin/*` endpoints
  (device registry, recipe injection). If unset, a random dev-mode key is
  generated once per process and logged as a warning; this must never be
  relied on outside local development.
- `signing_private_key_path` — where the backend's Ed25519 recipe-signing
  key (`agritwin_core.recipe_signing`) is persisted as PEM. Generated on
  first run if the file does not exist yet (see `signing.py`).
"""

from __future__ import annotations

import logging
from functools import lru_cache

from agritwin_core.device_auth import generate_api_key
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Persistence -------------------------------------------------------
    # SQLite file, chosen for this Gate 1 skeleton (CLAUDE.md rule 4: boring
    # technology wins). The real target — PostgreSQL on the single VPS — is
    # documented in docker-compose.yml / docs/architecture.md#10; standing
    # that up is out of scope here. Kept behind `database_url` so that
    # migration touches this one property, not every call site.
    database_path: str = Field(
        default="agritwin_api.db",
        description="SQLite database file path. File-based so state survives a restart.",
    )

    # --- Admin auth ----------------------------------------------------------
    admin_api_key: str | None = Field(
        default=None,
        description=(
            "Bearer token required for /admin/* endpoints. If unset, a "
            "dev-mode key is generated at process start and logged as a "
            "warning — set this explicitly for anything beyond local dev."
        ),
    )

    # --- Recipe signing --------------------------------------------------
    signing_private_key_path: str = Field(
        default="signing_key.pem",
        description=(
            "PEM file holding the backend's Ed25519 recipe-signing private "
            "key (agritwin_core.recipe_signing). Generated on first run if "
            "absent; regenerating it invalidates every device's embedded "
            "public key."
        ),
    )

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path}"


@lru_cache
def get_settings() -> Settings:
    """Process-wide cached settings instance. Import this, not `Settings()`
    directly, so the `.env` file is parsed once."""
    return Settings()


@lru_cache
def get_admin_api_key() -> str:
    """The effective admin bearer token for this process. Cached so a
    generated dev-mode key stays stable for the process lifetime."""
    settings = get_settings()
    if settings.admin_api_key:
        return settings.admin_api_key
    key = generate_api_key()
    logger.warning(
        "ADMIN_API_KEY not set; generated a dev-mode admin key for this "
        "process only (it will change on restart). Set ADMIN_API_KEY in "
        ".env for anything beyond local development. key=%s",
        key,
    )
    return key

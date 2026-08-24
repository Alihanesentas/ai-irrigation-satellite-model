"""Central secrets abstraction layer.

Nowhere else in agritwin_etl should call `os.getenv` directly. Every credential
and connection parameter is read through `Settings` below, and every other
module imports `Settings` (or the `get_settings()` accessor) rather than
reading the environment itself.

Why this matters here specifically: the project starts with a plain `.env`
file today and plans to move to Docker secrets later (confirmed in project
discussion — start simple, migrate once the compose stack is running). If call
sites read `os.getenv("SENTINEL_HUB_CLIENT_SECRET")` directly, that migration
touches every file that reads a credential. Because they instead depend on
`Settings`, the migration only ever touches this one file — swap
`env_file=".env"` for whatever loads Docker secrets into the environment (or a
custom `pydantic_settings` source), and no call site changes.

None of the fields below have real values yet. Fill in a project-root `.env`
(see `.env.example`, generated alongside this file) — this module intentionally
ships with everything unset so the ETL package fails loudly and specifically
(a clear "which credential is missing" error) rather than silently degrading.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- PostgreSQL + TimescaleDB (zone-day feature store, telemetry, logs) ---
    postgres_user: str | None = Field(
        default=None, description="TODO: fill in. TimescaleDB role for the ETL package."
    )
    postgres_password: str | None = Field(default=None, description="TODO: fill in.")
    postgres_host: str | None = Field(
        default=None, description="TODO: fill in. 'postgres' inside docker-compose network."
    )
    postgres_port: int | None = Field(default=5432, description="Default TimescaleDB/Postgres port.")
    postgres_db: str | None = Field(default="agritwin", description="Database name.")

    # --- MinIO (S3-compatible object storage for raw rasters) ---
    minio_root_user: str | None = Field(default=None, description="TODO: fill in.")
    minio_root_password: str | None = Field(default=None, description="TODO: fill in.")
    minio_endpoint: str | None = Field(
        default=None,
        description="TODO: fill in. 'minio:9000' inside docker-compose network.",
    )

    # --- Copernicus Data Space Ecosystem (Sentinel-2 L2A access) ---
    # See docs/decisions/data-access-layer.md: S2 via openEO / Sentinel Hub.
    sentinel_hub_client_id: str | None = Field(
        default=None, description="TODO: fill in. Copernicus Data Space OAuth client id."
    )
    sentinel_hub_client_secret: str | None = Field(
        default=None, description="TODO: fill in. Copernicus Data Space OAuth client secret."
    )

    # --- NASA Earthdata (SMAP soil moisture, primary source) ---
    # See docs/decisions/soil-moisture-data-access.md: SMAP is the primary
    # assimilation input; ISMN below is the independent cross-validation path.
    nasa_earthdata_username: str | None = Field(default=None, description="TODO: fill in.")
    nasa_earthdata_password: str | None = Field(default=None, description="TODO: fill in.")

    # --- ISMN (soil moisture cross-validation pipeline) ---
    ismn_username: str | None = Field(default=None, description="TODO: fill in.")
    ismn_password: str | None = Field(default=None, description="TODO: fill in.")

    # --- Copernicus Climate Data Store (ERA5-Land archive/training forcing) ---
    # See docs/decisions/weather-forcing-split.md: archive line only, never
    # the operational inference path.
    copernicus_cds_api_key: str | None = Field(default=None, description="TODO: fill in.")

    # --- USGS M2M (Landsat, fallback/alternate STAC access route) ---
    # See docs/decisions/landsat-data-access.md: Microsoft Planetary Computer
    # STAC is primary and needs no credential; USGS M2M is the fallback and
    # is what these fields authenticate.
    usgs_m2m_username: str | None = Field(default=None, description="TODO: fill in.")
    usgs_m2m_token: str | None = Field(default=None, description="TODO: fill in.")

    # --- Open-Meteo (operational weather forcing line) ---
    # Open-Meteo's free tier requires no API key. This field is present for
    # symmetry and for the day a paid tier or a different aggregator is
    # substituted; it can stay unset.
    open_meteo_api_key: str | None = Field(
        default=None,
        description="Optional. Open-Meteo's free tier needs no key; set only if upgrading tiers.",
    )


@lru_cache
def get_settings() -> Settings:
    """Process-wide cached settings instance. Import this, not `Settings()`
    directly, so the `.env` file is parsed once."""
    return Settings()

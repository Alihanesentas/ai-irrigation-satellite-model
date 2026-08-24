"""Dagster Definitions entry point — wires all assets and resources together.

Referenced by workspace.yaml. This is the single object Dagster loads to
build the asset graph shown in the webserver UI and executed by the daemon.
"""

from __future__ import annotations

import dagster as dg

from agritwin_etl.assets import all_assets
from agritwin_etl.config import get_settings


class PostgresResource(dg.ConfigurableResource):
    """Stub TimescaleDB/PostgreSQL connection resource.

    Real connection pooling (e.g. via SQLAlchemy or psycopg) is not wired yet
    — every asset in agritwin_etl.assets currently raises NotImplementedError
    before reaching persistence. Reads connection parameters from
    agritwin_etl.config.Settings, not from its own env lookups, to keep the
    single secrets abstraction point.
    """

    def get_connection_string(self) -> str:
        settings = get_settings()
        if not settings.postgres_user or not settings.postgres_password:
            raise NotImplementedError(
                "PostgresResource: Settings.postgres_user/postgres_password not "
                "set. Fill in .env before this resource can connect."
            )
        return (
            f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )


class MinIOResource(dg.ConfigurableResource):
    """Stub MinIO (S3-compatible) object storage resource for raw rasters.

    Reads connection parameters from agritwin_etl.config.Settings. Real S3
    client wiring (boto3 or similar) is not implemented yet.
    """

    def get_client_config(self) -> dict[str, str | None]:
        settings = get_settings()
        if not settings.minio_root_user or not settings.minio_root_password:
            raise NotImplementedError(
                "MinIOResource: Settings.minio_root_user/minio_root_password "
                "not set. Fill in .env before this resource can connect."
            )
        return {
            "endpoint_url": settings.minio_endpoint,
            "aws_access_key_id": settings.minio_root_user,
            "aws_secret_access_key": settings.minio_root_password,
        }


defs = dg.Definitions(
    assets=all_assets,
    resources={
        "postgres": PostgresResource(),
        "minio": MinIOResource(),
    },
)

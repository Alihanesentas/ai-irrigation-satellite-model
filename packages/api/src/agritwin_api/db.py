"""Persistence layer — SQLite via SQLAlchemy, file-based so state survives a
restart.

This is the single module that knows about storage. Every other module in
agritwin_api reaches the database through `get_session()` (a FastAPI
dependency) and the row classes below, never through a raw connection.
That is what makes swapping SQLite for the PostgreSQL target in
docs/architecture.md#10 a change confined to this file and `config.py`
(same rationale as `agritwin_etl.config.Settings`).

Rows store the corresponding `agritwin_core.schema` model as canonical JSON
text (`model_dump_json()` / `model_validate_json()`) rather than exploding
every field into a column. This is a Gate 1 skeleton, not the final
Postgres/TimescaleDB schema (docs/architecture.md#10) — the JSON columns
keep this module a thin, low-risk shim rather than a second, drifting copy
of the schemas in `agritwin_core.schema`. `device_id` / `parcel_id` /
`log_id` are pulled out as real columns because every query in this
package filters or looks up by them.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from functools import lru_cache

from sqlalchemy import DateTime, Engine, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from agritwin_api.config import get_settings


class Base(DeclarativeBase):
    pass


class DeviceRow(Base):
    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(String, primary_key=True)
    parcel_id: Mapped[str] = mapped_column(String, index=True)
    api_key_hash: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    firmware_version: Mapped[str | None] = mapped_column(String, nullable=True)
    provisioned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ParcelRecipeRow(Base):
    """The latest signed recipe for a parcel. Not versioned/kept as history
    in this skeleton — only the current recipe is stored, replacing
    whatever was there before (docs/architecture.md#4 recipe contract)."""

    __tablename__ = "parcel_recipes"

    parcel_id: Mapped[str] = mapped_column(String, primary_key=True)
    recipe_json: Mapped[str] = mapped_column(Text)


class TelemetryRow(Base):
    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    telemetry_json: Mapped[str] = mapped_column(Text)


class IrrigationLogRow(Base):
    """Idempotent on `log_id` — docs/schemas.md: 'devices retry uploads
    after connectivity loss.'"""

    __tablename__ = "irrigation_logs"

    log_id: Mapped[str] = mapped_column(String, primary_key=True)
    device_id: Mapped[str] = mapped_column(String, index=True)
    log_json: Mapped[str] = mapped_column(Text)


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


_session_factory: sessionmaker[Session] | None = None


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def reset_session_factory() -> None:
    """Test-only hook: forces `get_session_factory()` to rebuild against
    whatever engine `get_engine()` currently returns (e.g. after
    `get_engine.cache_clear()` points at a fresh test database)."""
    global _session_factory
    _session_factory = None


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request, committed on success,
    rolled back on any exception."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

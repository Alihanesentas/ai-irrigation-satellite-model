# packages/api — Cloud backend

Transport, identity, persistence, device registry, telemetry ingest. Owns no
business logic. Full responsibility and boundaries: `docs/modules.md#cloud-backend`.

**Status:** in progress — Phase 1 (Platform track), Gate 1.
`docs/delivery-plan.md`: the Platform track "gates on Nothing" — the old Phase-0-as-hard-gate
rule was superseded, see `docs/superseded-decisions.md`.

## What's here

A FastAPI skeleton implementing the Gate 1 "Backend" bullet: device registry,
recipe fetch (poll + `304`), telemetry ingest, per-device credential. No
decision engine exists yet (Phase 2, `packages/decision/`) — recipes are
injected via `PUT /admin/parcels/{parcel_id}/recipe` as a stand-in.

Persistence is file-based SQLite (`agritwin_api.db` by default) behind
`agritwin_api/db.py` — the real target is PostgreSQL on the single VPS
(`docs/architecture.md#10`); swapping later is confined to `db.py` and
`config.py`. The backend's Ed25519 recipe-signing keypair
(`agritwin_core.recipe_signing`) is generated on first run and persisted as
PEM at `signing_key.pem` by default.

## Running

```bash
cd packages/api
uv sync
uv run uvicorn agritwin_api.main:app --reload
```

The app is importable as `agritwin_api.main:app`. Configuration
(`agritwin_api/config.py`, `pydantic-settings`, `.env`-backed) follows the
same single-abstraction-point pattern as `agritwin_etl.config.Settings`:
`DATABASE_PATH`, `ADMIN_API_KEY`, `SIGNING_PRIVATE_KEY_PATH`. If
`ADMIN_API_KEY` is unset, a dev-mode key is generated at process start and
logged as a warning — set it explicitly for anything beyond local
development.

## Testing

```bash
cd packages/api
uv sync
uv run pytest -q
```

Tests use `fastapi.testclient.TestClient` directly against the `app` object
(no separate server process); each test gets an isolated temp SQLite file
and signing keypair via the `isolated_app_state` fixture in
`tests/conftest.py`.

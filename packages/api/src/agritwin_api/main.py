"""FastAPI application entrypoint.

Importable as `agritwin_api.main:app` — this exact path is depended on by
other packages' test suites (e.g. a device simulator / Gate 1 conformance
suite). Do not rename `app` or move it.
"""

from __future__ import annotations

from fastapi import FastAPI

from agritwin_api.routers import admin, devices, health

app = FastAPI(
    title="AgriTwin cloud backend",
    description=(
        "Transport, identity, persistence, device registry, telemetry "
        "ingest. Owns no business logic — see docs/modules.md#cloud-backend."
    ),
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(admin.router)
app.include_router(devices.router)

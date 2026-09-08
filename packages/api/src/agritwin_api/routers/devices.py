"""Device-facing API — recipe poll, telemetry ingest, irrigation-log ingest.

The device polls; the cloud never pushes (docs/architecture.md#5). Every
route here authenticates via `agritwin_api.security.get_authenticated_device`
(per-device API key, docs/architecture.md#11).
"""

from __future__ import annotations

from datetime import datetime

from agritwin_core.schema import DeviceStatus, IrrigationLog, Recipe, Telemetry
from agritwin_core.units import utc_now
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agritwin_api.db import DeviceRow, IrrigationLogRow, ParcelRecipeRow, TelemetryRow, get_session
from agritwin_api.security import get_authenticated_device

router = APIRouter(prefix="/devices", tags=["devices"])


class RecipePollResponse(BaseModel):
    server_time_utc: datetime
    recipe: Recipe | None


class ServerTimeResponse(BaseModel):
    server_time_utc: datetime


def _touch_device(device: DeviceRow, now: datetime, session: Session) -> None:
    """Successful poll bookkeeping (docs/architecture.md#7 edge state
    machine): update last_seen_at, and promote provisioned -> active on the
    device's first successful contact."""
    device.last_seen_at = now
    if device.status == DeviceStatus.PROVISIONED.value:
        device.status = DeviceStatus.ACTIVE.value
    session.add(device)


@router.get("/{device_id}/recipe")
def poll_recipe(
    device_id: str,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    device: DeviceRow = Depends(get_authenticated_device),
    session: Session = Depends(get_session),
) -> Response:
    # CLAUDE.md rule 6 (safe default is closed): a suspended device gets no
    # recipe at all, regardless of what is stored for its parcel.
    if device.status == DeviceStatus.SUSPENDED.value:
        raise HTTPException(status_code=403, detail="Device is suspended")

    now = utc_now()
    recipe_row = session.get(ParcelRecipeRow, device.parcel_id)
    if recipe_row is None:
        body = RecipePollResponse(server_time_utc=now, recipe=None)
        return JSONResponse(status_code=404, content=jsonable_encoder(body))

    recipe = Recipe.model_validate_json(recipe_row.recipe_json)
    _touch_device(device, now, session)

    etag = (if_none_match or "").strip().strip('"')
    if etag and etag == recipe.recipe_id:
        return Response(status_code=304)

    body = RecipePollResponse(server_time_utc=now, recipe=recipe)
    return JSONResponse(status_code=200, content=jsonable_encoder(body))


@router.post("/{device_id}/telemetry", response_model=ServerTimeResponse)
def ingest_telemetry(
    device_id: str,
    payload: Telemetry,
    device: DeviceRow = Depends(get_authenticated_device),
    session: Session = Depends(get_session),
) -> ServerTimeResponse:
    # docs/schemas.md: "The server returns its own time in every poll
    # response." ts_utc and clock_skew_s are always server-computed,
    # regardless of what the device sent — devices have no NTP.
    now = utc_now()
    skew_s = round((now - payload.device_ts_utc).total_seconds())
    stored = payload.model_copy(
        update={"device_id": device_id, "ts_utc": now, "clock_skew_s": skew_s}
    )

    row = TelemetryRow(
        device_id=device_id, received_at=now, telemetry_json=stored.model_dump_json()
    )
    session.add(row)
    return ServerTimeResponse(server_time_utc=now)


@router.post("/{device_id}/irrigation-logs", response_model=IrrigationLog)
def ingest_irrigation_log(
    device_id: str,
    payload: IrrigationLog,
    device: DeviceRow = Depends(get_authenticated_device),
    session: Session = Depends(get_session),
) -> IrrigationLog:
    log_id = str(payload.log_id)
    existing = session.get(IrrigationLogRow, log_id)
    if existing is not None:
        # Idempotent on log_id (docs/schemas.md): return the existing
        # record unchanged, do not error, do not overwrite.
        return IrrigationLog.model_validate_json(existing.log_json)

    stored = payload.model_copy(update={"device_id": device_id})
    row = IrrigationLogRow(
        log_id=log_id, device_id=device_id, log_json=stored.model_dump_json()
    )
    session.add(row)
    return stored

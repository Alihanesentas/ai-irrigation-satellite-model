"""Admin API — device provisioning and recipe injection.

`PUT /admin/parcels/{parcel_id}/recipe` stands in for the decision engine
(`packages/decision/`, Phase 2, not started — docs/modules.md#decision-engine).
This backend owns no business logic (docs/modules.md#cloud-backend); it only
signs and stores whatever recipe it is handed.
"""

from __future__ import annotations

from agritwin_core.device_auth import generate_api_key, hash_api_key
from agritwin_core.recipe_signing import public_key_to_pem, sign_recipe
from agritwin_core.schema import DeviceStatus, Recipe
from agritwin_core.units import utc_now
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agritwin_api.db import DeviceRow, ParcelRecipeRow, get_session
from agritwin_api.security import require_admin
from agritwin_api.signing import get_signing_keys

router = APIRouter(prefix="/admin", tags=["admin"])


class DeviceProvisionRequest(BaseModel):
    device_id: str
    parcel_id: str


class DeviceProvisionResponse(BaseModel):
    device_id: str
    parcel_id: str
    api_key: str


@router.post(
    "/devices",
    status_code=201,
    response_model=DeviceProvisionResponse,
    dependencies=[Depends(require_admin)],
)
def provision_device(
    payload: DeviceProvisionRequest, session: Session = Depends(get_session)
) -> DeviceProvisionResponse:
    if session.get(DeviceRow, payload.device_id) is not None:
        raise HTTPException(status_code=409, detail="device_id already exists")

    raw_key = generate_api_key()
    row = DeviceRow(
        device_id=payload.device_id,
        parcel_id=payload.parcel_id,
        api_key_hash=hash_api_key(raw_key),
        status=DeviceStatus.PROVISIONED.value,
        firmware_version=None,
        provisioned_at=utc_now(),
        last_seen_at=None,
    )
    session.add(row)
    return DeviceProvisionResponse(
        device_id=row.device_id, parcel_id=row.parcel_id, api_key=raw_key
    )


@router.put(
    "/parcels/{parcel_id}/recipe",
    response_model=Recipe,
    dependencies=[Depends(require_admin)],
)
def put_parcel_recipe(
    parcel_id: str, payload: Recipe, session: Session = Depends(get_session)
) -> Recipe:
    if payload.parcel_id != parcel_id:
        raise HTTPException(
            status_code=400, detail="recipe.parcel_id must match the path parcel_id"
        )

    private_key, _ = get_signing_keys()
    # sign_recipe's canonical payload excludes `signature`, so any value the
    # caller sent there is ignored — the stored recipe's signature always
    # matches its own content.
    signed = sign_recipe(payload, private_key)

    row = session.get(ParcelRecipeRow, parcel_id)
    if row is None:
        row = ParcelRecipeRow(parcel_id=parcel_id, recipe_json=signed.model_dump_json())
        session.add(row)
    else:
        row.recipe_json = signed.model_dump_json()
    return signed


@router.get("/signing-public-key")
def get_signing_public_key() -> dict[str, str]:
    """Public key PEM for the backend's Ed25519 recipe-signing key. No admin
    auth required — it is, by definition, public: the device simulator and
    firmware need it to verify recipes (docs/architecture.md#4, #11)."""
    _, public_key = get_signing_keys()
    return {"public_key_pem": public_key_to_pem(public_key)}

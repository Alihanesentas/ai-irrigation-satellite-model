"""Auth dependencies shared by routers.

Two credential kinds, per docs/architecture.md#11:

- Device-facing endpoints: `Authorization: Bearer <raw_api_key>`, checked
  against the per-device hash via `agritwin_core.device_auth.verify_api_key`.
- Admin endpoints (device provisioning, recipe injection — a stand-in for
  the not-yet-built decision engine, Phase 2): `Authorization: Bearer
  <ADMIN_API_KEY>`.
"""

from __future__ import annotations

import secrets

from agritwin_core.device_auth import verify_api_key
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from agritwin_api.config import get_admin_api_key
from agritwin_api.db import DeviceRow, get_session


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=401, detail="Authorization header must be 'Bearer <token>'"
        )
    return token


def get_authenticated_device(
    device_id: str,
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> DeviceRow:
    """Resolves and authenticates the device named by the `device_id` path
    parameter. Raises 401 on any missing/malformed header, unknown device,
    or key mismatch — CLAUDE.md rule 6, never leak which part failed."""
    token = _extract_bearer_token(authorization)
    device = session.get(DeviceRow, device_id)
    if device is None or not verify_api_key(token, device.api_key_hash):
        raise HTTPException(status_code=401, detail="Invalid device credentials")
    return device


def require_admin(authorization: str | None = Header(default=None)) -> None:
    token = _extract_bearer_token(authorization)
    expected = get_admin_api_key()
    if not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")

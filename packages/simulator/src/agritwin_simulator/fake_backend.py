"""In-memory test double for the cloud backend's device-facing surface.

Implements exactly the HTTP contract described in the task brief and
docs/architecture.md#4-5 / docs/schemas.md — the same contract `packages/api`
is being built against in parallel. All cryptography (signing, verification,
API-key hashing) goes through the real `agritwin_core.recipe_signing` /
`agritwin_core.device_auth` — only storage and transport are faked, per the
task brief: "no shortcuts there — only the storage/transport is faked".

Wire it to `DeviceSimulator` with::

    transport = httpx.MockTransport(fake_backend.handle_request)

so the whole conformance suite is self-contained and needs no running
`packages/api` instance.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agritwin_core.device_auth import hash_api_key, verify_api_key
from agritwin_core.recipe_signing import sign_recipe
from agritwin_core.schema import DeviceStatus, IrrigationLog, Recipe, Telemetry
from agritwin_core.units import utc_now


@dataclass
class _DeviceRecord:
    device_id: str
    parcel_id: str
    api_key_hash: str
    status: DeviceStatus = DeviceStatus.ACTIVE


class FakeBackend:
    """Storage/transport double. Not a device — has no clock of its own
    beyond `agritwin_core.units.utc_now()`, used only to stamp
    `server_time_utc` in poll responses (real-world clock discipline signal;
    conformance tests exercise skew by giving the *device* a different
    `VirtualClock` start, not by faking this)."""

    def __init__(self, private_key: Ed25519PrivateKey) -> None:
        self._private_key = private_key
        self._devices: dict[str, _DeviceRecord] = {}
        self._recipes: dict[str, Recipe] = {}  # parcel_id -> current signed recipe

        # Test/inspection surfaces.
        self.telemetry_log: list[Telemetry] = []
        self.irrigation_logs: dict[str, IrrigationLog] = {}  # log_id (str) -> log

        # Fault injection knobs for conformance scenarios.
        self.unreachable: bool = False
        self._fail_telemetry_next: int = 0
        self._fail_logs_next: int = 0

    # --- admin / test fixture setup ------------------------------------

    def register_device(
        self,
        device_id: str,
        parcel_id: str,
        raw_api_key: str,
        *,
        status: DeviceStatus = DeviceStatus.ACTIVE,
    ) -> None:
        self._devices[device_id] = _DeviceRecord(
            device_id=device_id,
            parcel_id=parcel_id,
            api_key_hash=hash_api_key(raw_api_key),
            status=status,
        )

    def suspend_device(self, device_id: str) -> None:
        self._devices[device_id].status = DeviceStatus.SUSPENDED

    def put_recipe(self, parcel_id: str, recipe: Recipe) -> Recipe:
        """Admin equivalent of `PUT /admin/parcels/{parcel_id}/recipe`: takes
        an unsigned (or ignore-signature) Recipe-shaped body, signs it with
        the backend's Ed25519 key, and serves it from then on via
        `GET /devices/{device_id}/recipe`."""
        signed = sign_recipe(recipe, self._private_key)
        self._recipes[parcel_id] = signed
        return signed

    def clear_recipe(self, parcel_id: str) -> None:
        self._recipes.pop(parcel_id, None)

    def store_raw_recipe(self, parcel_id: str, recipe: Recipe) -> None:
        """Store a recipe exactly as given, bypassing `sign_recipe`. Test
        hook for the bad-signature scenarios (unsigned / wrong-key-signed
        payloads reaching the device) — a real backend would never do this,
        which is exactly the point."""
        self._recipes[parcel_id] = recipe

    def tamper_current_recipe(self, parcel_id: str, **field_overrides: object) -> Recipe:
        """Test helper for the bad/tampered-signature scenario: mutate a
        field on the already-signed recipe without re-signing, so the
        signature no longer covers the payload."""
        current = self._recipes[parcel_id]
        tampered = current.model_copy(update=field_overrides)
        self._recipes[parcel_id] = tampered
        return tampered

    def fail_next_telemetry(self, n: int = 1) -> None:
        self._fail_telemetry_next += n

    def fail_next_logs(self, n: int = 1) -> None:
        self._fail_logs_next += n

    # --- transport entrypoint -------------------------------------------

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if self.unreachable:
            raise httpx.ConnectError("simulated connectivity loss", request=request)

        path = urlsplit(str(request.url)).path
        parts = [p for p in path.split("/") if p]

        if len(parts) == 3 and parts[0] == "devices":
            device_id, resource = parts[1], parts[2]
            device = self._devices.get(device_id)
            auth_error = self._check_auth(request, device)
            if auth_error is not None:
                return auth_error
            assert device is not None  # _check_auth already rejected None

            if resource == "recipe" and request.method == "GET":
                return self._handle_get_recipe(request, device)
            if resource == "telemetry" and request.method == "POST":
                return self._handle_post_telemetry(request)
            if resource == "irrigation-logs" and request.method == "POST":
                return self._handle_post_log(request)

        return httpx.Response(404, json={"detail": "not found"})

    def _check_auth(
        self, request: httpx.Request, device: _DeviceRecord | None
    ) -> httpx.Response | None:
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return httpx.Response(401, json={"detail": "missing bearer token"})
        raw_key = auth_header[len("Bearer "):]
        if device is None or not verify_api_key(raw_key, device.api_key_hash):
            return httpx.Response(401, json={"detail": "invalid credentials"})
        if device.status == DeviceStatus.SUSPENDED:
            return httpx.Response(403, json={"detail": "device suspended"})
        return None

    def _handle_get_recipe(self, request: httpx.Request, device: _DeviceRecord) -> httpx.Response:
        server_time = utc_now().isoformat()
        recipe = self._recipes.get(device.parcel_id)
        if recipe is None:
            return httpx.Response(
                404, content=json.dumps({"server_time_utc": server_time, "recipe": None})
            )
        if_none_match = request.headers.get("if-none-match", "").strip('"')
        if if_none_match and if_none_match == recipe.recipe_id:
            return httpx.Response(304)
        return httpx.Response(
            200,
            content=json.dumps(
                {"server_time_utc": server_time, "recipe": recipe.model_dump(mode="json")}
            ),
        )

    def _handle_post_telemetry(self, request: httpx.Request) -> httpx.Response:
        if self._fail_telemetry_next > 0:
            self._fail_telemetry_next -= 1
            raise httpx.ConnectError("simulated telemetry upload failure", request=request)
        payload = json.loads(request.content)
        telemetry = Telemetry.model_validate(payload)
        self.telemetry_log.append(telemetry)
        return httpx.Response(
            200, content=json.dumps({"server_time_utc": utc_now().isoformat()})
        )

    def _handle_post_log(self, request: httpx.Request) -> httpx.Response:
        if self._fail_logs_next > 0:
            self._fail_logs_next -= 1
            raise httpx.ConnectError("simulated log upload failure", request=request)
        payload = json.loads(request.content)
        log = IrrigationLog.model_validate(payload)
        key = str(log.log_id)
        existing = self.irrigation_logs.get(key)
        if existing is None:
            self.irrigation_logs[key] = log
            existing = log
        # Idempotent on log_id: reposting the same id returns the stored
        # record rather than erroring or duplicating (docs/schemas.md).
        return httpx.Response(200, content=existing.model_dump_json())

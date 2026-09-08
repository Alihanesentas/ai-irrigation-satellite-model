from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agritwin_core.recipe_signing import public_key_from_pem, verify_recipe
from agritwin_core.schema import Recipe
from fastapi.testclient import TestClient

from .conftest import ADMIN_HEADERS


def _recipe_payload(parcel_id: str, recipe_id: str = "01J9X2EXAMPLE") -> dict:
    return {
        "schema_version": "1.0",
        "recipe_id": recipe_id,
        "parcel_id": parcel_id,
        "issued_at": "2026-08-18T02:10:00Z",
        "valid_from": "2026-08-18T00:00:00Z",
        "valid_until": "2026-08-20T00:00:00Z",
        "confidence": "normal",
        "fallback_policy": "no_irrigation",
        "zones": [
            {
                "zone_id": "z1",
                "events": [
                    {
                        "start_utc": "2026-08-18T02:30:00Z",
                        "duration_s": 5400,
                        "target_mm": 12.0,
                        "priority": 1,
                    }
                ],
            }
        ],
        "constraints": {
            "max_concurrent_zones": 1,
            "min_pressure_kpa": 150,
            "max_daily_mm": 20,
        },
    }


def _provision(client: TestClient, device_id: str, parcel_id: str) -> dict:
    resp = client.post(
        "/admin/devices",
        json={"device_id": device_id, "parcel_id": parcel_id},
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_provision_device_then_poll_with_no_recipe_returns_404_null(
    client: TestClient,
) -> None:
    device = _provision(client, "dev-1", "prc-1")

    resp = client.get(
        "/devices/dev-1/recipe",
        headers={"Authorization": f"Bearer {device['api_key']}"},
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["recipe"] is None
    # Just needs to be a parseable UTC timestamp.
    datetime.fromisoformat(body["server_time_utc"].replace("Z", "+00:00"))


def test_provision_duplicate_device_id_conflicts(client: TestClient) -> None:
    _provision(client, "dev-dup", "prc-1")
    resp = client.post(
        "/admin/devices",
        json={"device_id": "dev-dup", "parcel_id": "prc-2"},
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 409


def test_admin_injects_recipe_and_device_polls_signed_recipe(client: TestClient) -> None:
    device = _provision(client, "dev-2", "prc-2")

    put_resp = client.put(
        "/admin/parcels/prc-2/recipe",
        json=_recipe_payload("prc-2"),
        headers=ADMIN_HEADERS,
    )
    assert put_resp.status_code == 200, put_resp.text
    stored_recipe = put_resp.json()
    assert stored_recipe["signature"] is not None

    pubkey_resp = client.get("/admin/signing-public-key")
    assert pubkey_resp.status_code == 200
    public_key = public_key_from_pem(pubkey_resp.json()["public_key_pem"])

    poll_resp = client.get(
        "/devices/dev-2/recipe",
        headers={"Authorization": f"Bearer {device['api_key']}"},
    )
    assert poll_resp.status_code == 200
    body = poll_resp.json()
    recipe = Recipe.model_validate(body["recipe"])
    assert recipe.recipe_id == "01J9X2EXAMPLE"
    assert verify_recipe(recipe, public_key)


def test_poll_with_matching_if_none_match_returns_304(client: TestClient) -> None:
    device = _provision(client, "dev-3", "prc-3")
    client.put(
        "/admin/parcels/prc-3/recipe",
        json=_recipe_payload("prc-3", recipe_id="recipe-abc"),
        headers=ADMIN_HEADERS,
    )
    headers = {"Authorization": f"Bearer {device['api_key']}"}

    first = client.get("/devices/dev-3/recipe", headers=headers)
    assert first.status_code == 200

    second = client.get(
        "/devices/dev-3/recipe",
        headers={**headers, "If-None-Match": '"recipe-abc"'},
    )
    assert second.status_code == 304
    assert second.content == b""


def test_poll_missing_or_wrong_api_key_is_401(client: TestClient) -> None:
    _provision(client, "dev-4", "prc-4")

    no_auth = client.get("/devices/dev-4/recipe")
    assert no_auth.status_code == 401

    wrong_key = client.get(
        "/devices/dev-4/recipe", headers={"Authorization": "Bearer not-the-right-key"}
    )
    assert wrong_key.status_code == 401


def test_poll_suspended_device_is_403(client: TestClient) -> None:
    device = _provision(client, "dev-5", "prc-5")

    from agritwin_api.db import DeviceRow, get_engine
    from sqlalchemy.orm import Session as OrmSession

    with OrmSession(get_engine()) as session:
        row = session.get(DeviceRow, "dev-5")
        row.status = "suspended"
        session.commit()

    resp = client.get(
        "/devices/dev-5/recipe",
        headers={"Authorization": f"Bearer {device['api_key']}"},
    )
    assert resp.status_code == 403


def test_telemetry_ingest_overrides_ts_and_clock_skew_server_side(
    client: TestClient,
) -> None:
    device = _provision(client, "dev-6", "prc-6")
    device_ts = datetime.now(timezone.utc) - timedelta(seconds=30)

    payload = {
        "device_id": "dev-6",
        "ts_utc": "1999-01-01T00:00:00Z",  # bogus client value, must be ignored
        "device_ts_utc": device_ts.isoformat(),
        "clock_skew_s": 999999,  # bogus client value, must be ignored
        "firmware_version": "1.0.0",
        "state": "sleep",
        "battery_mv": 3700,
        "solar_mv": None,
        "rssi_dbm": -70,
        "comms_tech": "nbiot",
        "uptime_s": 1000,
        "last_recipe_id": None,
        "recipe_valid_until": (device_ts + timedelta(days=1)).isoformat(),
        "fault_flags": 0,
        "pending_log_count": 0,
    }

    resp = client.post(
        "/devices/dev-6/telemetry",
        json=payload,
        headers={"Authorization": f"Bearer {device['api_key']}"},
    )
    assert resp.status_code == 200
    server_time = datetime.fromisoformat(resp.json()["server_time_utc"])
    assert abs((server_time - datetime.now(timezone.utc)).total_seconds()) < 5

    from agritwin_api.db import TelemetryRow, get_engine
    from sqlalchemy.orm import Session as OrmSession
    from agritwin_core.schema import Telemetry

    with OrmSession(get_engine()) as session:
        row = session.query(TelemetryRow).filter_by(device_id="dev-6").one()
        stored = Telemetry.model_validate_json(row.telemetry_json)

    assert stored.ts_utc.year != 1999
    assert 25 <= stored.clock_skew_s <= 35


def test_irrigation_log_ingest_is_idempotent_on_log_id(client: TestClient) -> None:
    device = _provision(client, "dev-7", "prc-7")
    headers = {"Authorization": f"Bearer {device['api_key']}"}

    payload = {
        "log_id": "5b1b6f1e-1c1a-4a1a-9a1a-1a1a1a1a1a1a",
        "device_id": "dev-7",
        "zone_id": "z1",
        "recipe_id": "recipe-1",
        "event_index": 0,
        "firmware_version": "1.0.0",
        "commanded_start_utc": "2026-08-18T02:30:00Z",
        "actual_start_utc": "2026-08-18T02:30:05Z",
        "commanded_duration_s": 5400,
        "actual_duration_s": 5400,
        "commanded_target_mm": 12.0,
        "meter_pulses": 1000,
        "meter_k_factor_l_per_pulse": 0.5,
        "measured_volume_l": 500.0,
        "measured_depth_mm": 11.5,
        "flow_rate_mean_l_min": 5.5,
        "flow_rate_p10_l_min": 5.0,
        "flow_rate_p90_l_min": 6.0,
        "pressure_ok": True,
        "pressure_fault_count": 0,
        "termination_reason": "duration_reached",
        "data_quality": "ok",
    }

    first = client.post("/devices/dev-7/irrigation-logs", json=payload, headers=headers)
    assert first.status_code == 200
    second = client.post("/devices/dev-7/irrigation-logs", json=payload, headers=headers)
    assert second.status_code == 200
    assert first.json() == second.json()

    from agritwin_api.db import IrrigationLogRow, get_engine
    from sqlalchemy.orm import Session as OrmSession

    with OrmSession(get_engine()) as session:
        count = session.query(IrrigationLogRow).filter_by(log_id=payload["log_id"]).count()
    assert count == 1

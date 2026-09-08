"""Gate 1 conformance: a telemetry POST fails/times out — the device keeps
operating, retries (sends a fresh telemetry record) on the next Sync, and
this never blocks irrigation.
"""

from __future__ import annotations

from agritwin_simulator import DeviceState


def test_telemetry_failure_does_not_block_operation_or_crash(
    backend, clock, make_device, make_recipe
):
    recipe = make_recipe(now=clock.now())
    backend.put_recipe(recipe.parcel_id, recipe)
    backend.fail_next_telemetry(1)

    device = make_device()
    # First Sync: telemetry POST fails, but the recipe fetch/verify/arm path
    # is unaffected — it still arms successfully.
    device.wake_and_sync()

    assert device.state == DeviceState.ARMED
    assert len(backend.telemetry_log) == 0  # the failed attempt was not recorded
    assert len(device.telemetry_sent) == 0

    # Irrigation proceeds normally afterward, and by the next Sync
    # (recipe fully executed and expired) telemetry succeeds again.
    device.run_for(24 * 3600 + 60)

    assert device.state == DeviceState.SLEEP
    assert len(backend.irrigation_logs) == 1
    assert len(backend.telemetry_log) >= 1

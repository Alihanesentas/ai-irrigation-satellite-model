"""Gate 1 conformance: clock skew — the backend's `server_time_utc` differs
from the device's own clock. Must be recorded (docs/schemas.md
TELEMETRY.clock_skew_s) and must not crash or corrupt scheduling: the
device still executes against its own local clock (docs/architecture.md#7:
"local clock is UTC plus an explicit offset").
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from agritwin_simulator import DeviceState


def test_clock_skew_is_recorded_and_does_not_corrupt_scheduling(
    backend, clock, make_device, make_recipe
):
    recipe = make_recipe(now=clock.now())
    backend.put_recipe(recipe.parcel_id, recipe)

    device = make_device()

    # Make the backend's clock read 10 minutes ahead of the device's.
    skewed_backend_now = clock.now() + timedelta(minutes=10)
    with patch("agritwin_simulator.fake_backend.utc_now", return_value=skewed_backend_now):
        device.wake_and_sync()

    assert device.state == DeviceState.ARMED
    assert device.clock_skew_s is not None
    # device_now - server_now ~= -600s (device behind the skewed server clock)
    assert -601 <= device.clock_skew_s <= -599

    # Scheduling still proceeds off the device's own (unskewed) clock — the
    # event fires and completes without error.
    device.run_for(24 * 3600 + 60)
    assert device.state == DeviceState.SLEEP
    assert len(backend.irrigation_logs) == 1

"""Gate 1 conformance: a valid, signed, in-window recipe executed correctly
end-to-end — poll -> verify -> arm -> irrigate -> log.
docs/delivery-plan.md "The integration guarantee", scenario list.
"""

from __future__ import annotations

from agritwin_core.schema import TerminationReason
from agritwin_simulator import DeviceState


def test_valid_recipe_executes_end_to_end(backend, clock, make_device, make_recipe, zone_id):
    recipe = make_recipe(now=clock.now())
    backend.put_recipe(recipe.parcel_id, recipe)

    device = make_device()
    device.run_for(24 * 3600 + 60)  # cover the full 24h validity plus a margin

    # Executed the one scheduled event, uploaded its log, and returned to
    # Sleep once the (now fully executed) recipe's validity window ended.
    assert device.state == DeviceState.SLEEP
    assert len(backend.irrigation_logs) == 1
    log = next(iter(backend.irrigation_logs.values()))
    assert log.zone_id == zone_id
    assert log.recipe_id == recipe.recipe_id
    assert log.termination_reason in (
        TerminationReason.DURATION_REACHED,
        TerminationReason.TARGET_MM_REACHED,
    )
    assert log.meter_pulses > 0
    assert log.measured_depth_mm.value > 0
    # Telemetry was reported and reflects no backlog.
    assert len(backend.telemetry_log) >= 1
    assert device.pending_log_count == 0

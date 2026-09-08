"""Gate 1 conformance: `target_mm` early-abort. `duration_s` is what the
device would otherwise execute; if the flow meter reaches `target_mm`
(zone-average depth) first, the device stops early with
`TARGET_MM_REACHED` rather than running the full commanded duration.
docs/architecture.md#4.
"""

from __future__ import annotations

from agritwin_core.schema import TerminationReason
from agritwin_simulator import DeviceState


def test_low_target_mm_triggers_early_abort(backend, clock, make_device, make_recipe):
    # duration_s is generous (1 hour); nominal flow is fast enough (default
    # 60 L/min over 500 m2) that a small target_mm is reached well before
    # duration_s elapses.
    recipe = make_recipe(now=clock.now(), duration_s=3600, target_mm=1.0)
    backend.put_recipe(recipe.parcel_id, recipe)

    device = make_device()
    device.run_for(24 * 3600 + 60)

    assert device.state == DeviceState.SLEEP
    assert len(backend.irrigation_logs) == 1
    log = next(iter(backend.irrigation_logs.values()))
    assert log.termination_reason == TerminationReason.TARGET_MM_REACHED
    assert log.actual_duration_s < log.commanded_duration_s
    assert log.measured_depth_mm.value <= 1.05  # close to target_mm, allowing meter quantisation


def test_zero_target_mm_runs_full_duration(backend, clock, make_device, make_recipe):
    recipe = make_recipe(now=clock.now(), duration_s=120, target_mm=0.0)
    backend.put_recipe(recipe.parcel_id, recipe)

    device = make_device()
    device.run_for(24 * 3600 + 60)

    log = next(iter(backend.irrigation_logs.values()))
    assert log.termination_reason == TerminationReason.DURATION_REACHED
    assert log.actual_duration_s == log.commanded_duration_s

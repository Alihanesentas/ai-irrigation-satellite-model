"""Gate 1 conformance: degradation ladder, docs/architecture.md#8.

L0-L3 are entirely about *what recipe the decision engine produces* (fresh
vs. stale forcing, low-confidence residual, bucket-model fallback when the
twin is unavailable) — they require packages/twin and packages/decision,
neither of which exists yet (Phase 2+, docs/modules.md). The edge node's
behaviour is identical in all four cases: execute whatever signed recipe it
receives. They are skipped here for that reason, per the task brief, and are
the twin/decision team's conformance surface once those packages exist.

L4-L6 are edge-observable and implemented + covered below.
"""

from __future__ import annotations

from datetime import timedelta

from agritwin_core.schema import TerminationReason
from agritwin_simulator import DeviceState, FaultInjection


def test_l4_no_forcing_serves_last_recipe_then_stops(backend, clock, make_device, make_recipe):
    """L4: weather/backend source unreachable during a poll -> the device
    keeps executing the recipe it already has until `valid_until`, then
    stops (does not re-arm a now-expired recipe even if the backend later
    re-serves the same one, e.g. because it has nothing new to offer)."""
    recipe = make_recipe(now=clock.now(), valid_for=timedelta(hours=1))
    backend.put_recipe(recipe.parcel_id, recipe)

    device = make_device(wake_interval_s=3600)
    device.run_for(3600 + 60)  # arms, executes the one event, then expires

    assert device.state == DeviceState.SLEEP
    assert len(backend.irrigation_logs) == 1

    # The backend never produces a fresh recipe (as if the weather/forcing
    # source were unreachable upstream) — it just keeps the same, now
    # stale, recipe on file. Further wakes must not re-execute it.
    device.run_for(3 * 24 * 3600)
    assert device.state == DeviceState.SLEEP
    assert len(backend.irrigation_logs) == 1  # unchanged — "then stop"


def test_l5_no_connectivity_executes_stored_recipe_then_falls_back(
    backend, clock, make_device, make_recipe
):
    """L5: device cannot reach the backend at all. It must still execute
    the already-armed recipe (offline, local clock) and then apply
    `fallback_policy` (no_irrigation) once it expires — never crash, never
    silently keep going past expiry."""
    recipe = make_recipe(now=clock.now(), valid_for=timedelta(hours=1))
    backend.put_recipe(recipe.parcel_id, recipe)

    device = make_device(wake_interval_s=3600)
    device.wake_and_sync()
    assert device.state == DeviceState.ARMED

    backend.unreachable = True
    device.run_for(3600 + 60)  # event fires, then expiry — all offline

    assert device.state == DeviceState.SLEEP
    assert device.current_recipe is None  # fallback applied, nothing repeated
    assert device.pending_log_count == 1  # log queued, backend unreachable
    assert len(backend.irrigation_logs) == 0

    # A further wake while still unreachable must not crash or misbehave.
    device.run_for(24 * 3600)
    assert device.state == DeviceState.SLEEP


def test_l6_hardware_fault_closes_valve_and_requires_ack(backend, clock, make_device, make_recipe):
    """L6: pressure/flow mismatch -> close the valve, flag it, and require
    an explicit acknowledgement before Armed is reachable again."""
    recipe = make_recipe(now=clock.now(), duration_s=1800, target_mm=8.0)
    backend.put_recipe(recipe.parcel_id, recipe)

    device = make_device()
    device.inject_fault(FaultInjection(at_elapsed_s=300, kind=TerminationReason.PRESSURE_FAULT))
    device.run_for(24 * 3600 + 60)

    assert device.state == DeviceState.FAULT
    assert device.valve_open is False  # closed before the log was recorded
    assert device.fault_flags != 0
    log = next(iter(backend.irrigation_logs.values()))
    assert log.termination_reason == TerminationReason.PRESSURE_FAULT
    assert log.pressure_ok is False

    # Cannot silently resume without an ack.
    device.run_for(3600)
    assert device.state == DeviceState.FAULT

    device.acknowledge_fault()
    assert device.state == DeviceState.ARMED
    assert device.fault_flags == 0

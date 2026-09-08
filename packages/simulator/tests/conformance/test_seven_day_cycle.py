"""Gate 1 exit criterion (docs/delivery-plan.md, Phase 1): "Simulator
completes an unattended 7-day cycle against fabricated recipes."

Drives the device through 7 simulated days of wake/poll/irrigate/report,
with a fresh daily recipe fabricated and served each day (mirroring the
daily cycle in docs/architecture.md#5 — one fresh signed recipe issued per
~02:00 UTC run, one wake/poll per day). Asserts it never reaches an
unrecovered Fault and never irrigates on an expired or unsigned recipe.
Must run in a few seconds of real wall-clock time — it drives a
`VirtualClock`, never `time.sleep`.
"""

from __future__ import annotations

import time
from datetime import timedelta

from agritwin_core.recipe_signing import generate_keypair, sign_recipe
from agritwin_core.schema import TerminationReason
from agritwin_simulator import DeviceState


def test_unattended_seven_day_cycle(backend, clock, make_device, make_recipe):
    device = make_device(wake_interval_s=24 * 3600)

    start_wall = time.monotonic()

    day_zero = clock.now()
    for day in range(7):
        day_start = day_zero + timedelta(days=day)
        recipe = make_recipe(
            now=day_start,
            recipe_id=f"r-day-{day}",
            valid_for=timedelta(hours=24),
            event_offset=timedelta(hours=1),
            duration_s=1800,
            target_mm=6.0,
        )
        backend.put_recipe(recipe.parcel_id, recipe)

        # One day of simulated time: wake, poll, verify, arm, irrigate,
        # report, expire back to Sleep, ready for tomorrow's recipe.
        device.run_for(24 * 3600)

        assert device.state == DeviceState.SLEEP
        assert device.current_recipe is None  # expired cleanly, nothing carried over

    wall_elapsed_s = time.monotonic() - start_wall
    assert wall_elapsed_s < 5.0, (
        f"7-day cycle took {wall_elapsed_s:.2f}s of real time — "
        "the virtual clock is not actually virtual"
    )

    # Never got stuck in an unrecovered Fault.
    assert device.state != DeviceState.FAULT

    # One executed event per day, all legitimate.
    assert len(backend.irrigation_logs) == 7
    for log in backend.irrigation_logs.values():
        assert log.termination_reason in (
            TerminationReason.DURATION_REACHED,
            TerminationReason.TARGET_MM_REACHED,
        )
    assert device.pending_log_count == 0

    # Telemetry was reported at least once per day.
    assert len(backend.telemetry_log) >= 7

    # Never armed against a tampered/unsigned recipe served mid-week.
    tampered_day = day_zero + timedelta(days=7)
    bad_recipe = make_recipe(now=tampered_day, recipe_id="r-day-7-bad", valid_for=timedelta(hours=24))
    other_private, _ = generate_keypair()
    backend.store_raw_recipe(bad_recipe.parcel_id, sign_recipe(bad_recipe, other_private))

    device.run_for(24 * 3600)
    assert device.state == DeviceState.SLEEP
    assert device.current_recipe is None
    assert len(backend.irrigation_logs) == 7  # unchanged — the bad recipe was never executed

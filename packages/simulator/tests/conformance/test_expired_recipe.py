"""Gate 1 conformance: expired recipe — `valid_until` passed before the
device ever polled for it means the device must apply `fallback_policy`
(no irrigation), never execute, and never repeat the last schedule.
docs/architecture.md#4 and #7.
"""

from __future__ import annotations

from datetime import timedelta

from agritwin_simulator import DeviceState


def test_recipe_already_expired_on_arrival_is_never_executed(backend, clock, make_device, make_recipe):
    now = clock.now()
    # valid_until is in the past relative to `now` by the time the device
    # would validate it.
    recipe = make_recipe(
        now=now - timedelta(hours=2),
        valid_for=timedelta(hours=1),
        event_offset=timedelta(minutes=5),
    )
    backend.put_recipe(recipe.parcel_id, recipe)

    device = make_device()
    device.wake_and_sync()

    assert device.state == DeviceState.SLEEP
    assert device.current_recipe is None
    assert len(backend.irrigation_logs) == 0


def test_recipe_expires_mid_armed_without_repeating_schedule(backend, clock, make_device, make_recipe):
    now = clock.now()
    # Valid for 1 hour, but the only event starts after that window closes
    # -> Armed sees valid_until before any event and expires without
    # executing, then does not re-arm the same schedule afterward.
    recipe = make_recipe(
        now=now,
        valid_for=timedelta(hours=1),
        event_offset=timedelta(hours=2),
    )
    backend.put_recipe(recipe.parcel_id, recipe)

    device = make_device(wake_interval_s=3600)
    device.run_for(3600 + 60)

    assert device.state == DeviceState.SLEEP
    assert device.current_recipe is None
    assert len(backend.irrigation_logs) == 0

    # A further wake with no new recipe re-served must not resurrect the
    # expired schedule.
    device.run_for(24 * 3600)
    assert device.state == DeviceState.SLEEP
    assert len(backend.irrigation_logs) == 0

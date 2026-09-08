"""Gate 1 conformance: 401 (bad/missing key) and 403 (suspended device) both
resolve to Sleep, never Armed and never executing anything — CLAUDE.md rule
6.
"""

from __future__ import annotations

from agritwin_simulator import DeviceState


def test_bad_api_key_never_arms(backend, clock, make_device, make_recipe):
    recipe = make_recipe(now=clock.now())
    backend.put_recipe(recipe.parcel_id, recipe)

    device = make_device(api_key="totally-wrong-key")
    device.wake_and_sync()

    assert device.state == DeviceState.SLEEP
    assert device.current_recipe is None


def test_suspended_device_never_arms(backend, clock, make_device, make_recipe):
    recipe = make_recipe(now=clock.now())
    backend.put_recipe(recipe.parcel_id, recipe)
    backend.suspend_device("dev-0001")

    device = make_device()
    device.wake_and_sync()

    assert device.state == DeviceState.SLEEP
    assert device.current_recipe is None
    assert len(backend.irrigation_logs) == 0

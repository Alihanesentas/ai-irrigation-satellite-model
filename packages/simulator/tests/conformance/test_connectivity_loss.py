"""Gate 1 conformance: connectivity loss mid-irrigation — the backend is
unreachable while an event is actively `Irrigating`. The event must still
complete locally against the already-stored (verified, armed) recipe; the
resulting log queues and uploads on the next successful Sync;
`pending_log_count` reflects the backlog in the meantime.
"""

from __future__ import annotations

from agritwin_simulator import DeviceState


def test_event_completes_locally_and_log_uploads_on_next_sync(
    backend, clock, make_device, make_recipe
):
    recipe = make_recipe(now=clock.now())
    backend.put_recipe(recipe.parcel_id, recipe)

    device = make_device()
    device.wake_and_sync()
    assert device.state == DeviceState.ARMED

    # Connectivity drops before the event fires and stays down through it.
    backend.unreachable = True
    device.run_for(35 * 60)  # covers the event's start + duration

    # The event executed locally regardless — Irrigating never depends on
    # the network (docs/architecture.md#7 executes "offline against its
    # local clock").
    assert device.state == DeviceState.ARMED
    assert device.pending_log_count == 1
    assert len(backend.irrigation_logs) == 0

    # Connectivity returns; the next Sync (recipe now expired -> Sleep)
    # drains the backlog.
    backend.unreachable = False
    device.run_for(24 * 3600)

    assert device.state == DeviceState.SLEEP
    assert device.pending_log_count == 0
    assert len(backend.irrigation_logs) == 1

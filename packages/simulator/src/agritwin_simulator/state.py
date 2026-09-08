"""The edge node state machine, docs/architecture.md#7, verbatim:

    Sleep --wake window--> Sync --no new recipe--> Sleep
    Sync --recipe received--> Validate
    Validate --signature or window invalid--> Sleep
    Validate --valid--> Armed
    Armed --event start time reached--> Irrigating
    Armed --valid_until passed--> Expired
    Irrigating --duration or target_mm reached--> Armed
    Irrigating --pressure or flow anomaly--> Fault
    Fault --operator ack--> Armed
    Expired --fallback applied--> Sleep

This module holds only the state enum. Transition logic lives in
`agritwin_simulator.device.DeviceSimulator` — kept separate so the
conformance suite (`tests/conformance/`) can assert on `device.state`
without importing simulator internals.
"""

from __future__ import annotations

from enum import Enum


class DeviceState(str, Enum):
    SLEEP = "sleep"
    SYNC = "sync"
    VALIDATE = "validate"
    ARMED = "armed"
    IRRIGATING = "irrigating"
    FAULT = "fault"
    EXPIRED = "expired"

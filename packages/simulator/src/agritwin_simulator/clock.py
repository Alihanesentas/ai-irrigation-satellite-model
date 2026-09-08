"""Virtual clock for the device simulator.

The Gate 1 exit criterion (docs/delivery-plan.md, Phase 1 "Exit criteria") is
an *unattended 7-day cycle* completing as a test — that only works if "7 days"
means 7 simulated days, not 7 real days of `time.sleep`. Every time source the
simulator touches must go through this class, never `datetime.now()` /
`time.sleep()` directly, so the whole state machine can be driven at
effectively infinite speed under test while still producing UTC-correct
`Recipe`/`IrrigationLog`/`Telemetry` timestamps (CLAUDE.md rule 5).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from agritwin_core.units import utc_now


class VirtualClock:
    """An explicit, advanceable stand-in for wall-clock time.

    Always UTC (CLAUDE.md rule 5) — there is no local-time notion here at
    all; per docs/architecture.md#7 local time is "UTC plus an explicit
    offset" applied only in the edge layer, and this simulator never needs
    to render local time, only to execute against UTC instants.
    """

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start if start is not None else utc_now()

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> datetime:
        """Move the clock forward by `seconds` of simulated time. Negative
        values are rejected — a device's local clock does not run
        backwards."""
        if seconds < 0:
            raise ValueError(f"cannot advance a clock by a negative amount: {seconds}")
        self._now = self._now + timedelta(seconds=seconds)
        return self._now

    def advance_to(self, target: datetime) -> datetime:
        """Jump forward to an absolute instant. Used by the simulator's run
        loop to skip directly to the next state-machine-relevant timestamp
        (next wake, next event start, `valid_until`) instead of ticking
        second by second — this is what makes a 7-day cycle run in
        milliseconds of real time."""
        if target < self._now:
            raise ValueError(
                f"cannot move a clock backwards: now={self._now!r}, target={target!r}"
            )
        self._now = target
        return self._now

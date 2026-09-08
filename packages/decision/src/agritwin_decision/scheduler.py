"""Multi-zone scheduling: a set of `ZoneIrrigationNeed`s -> an ordered list
of `(zone_id, RecipeEvent)` pairs respecting `RecipeConstraints`.

v1 is a **greedy sequential scheduler**, not a `scipy.optimize`/`cvxpy` joint
optimizer (`docs/modules.md` names the latter as the eventual stack). See
`docs/decisions/irrigation-trigger-policy.md` for why: with no real
multi-zone conflicting objective to optimize against yet, an LP formulation
would be complexity without a problem to solve. Zones are laid out
back-to-back in urgency order; `constraints.max_concurrent_zones` is
respected by construction (sequential = always 1 concurrent), and
`constraints.max_daily_mm` clamps each zone's applied depth, scaling its
duration down proportionally (duration is linear in depth at a fixed flow
rate, so no zone-config lookup is needed here to do that scaling).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from agritwin_core.schema import RecipeConstraints, RecipeEvent
from agritwin_core.units import DepthMM

from agritwin_decision.zone_plan import ZoneIrrigationNeed


def schedule_events(
    needs: list[ZoneIrrigationNeed],
    constraints: RecipeConstraints,
    start_at: datetime,
) -> list[tuple[str, RecipeEvent]]:
    """Most-urgent-first, back-to-back, one zone at a time. Empty `needs`
    returns an empty list — a day with no zone past its trigger produces a
    recipe with no events, not an error.
    """
    ordered = sorted(needs, key=lambda n: n.urgency, reverse=True)

    events: list[tuple[str, RecipeEvent]] = []
    current_time = start_at
    for priority, need in enumerate(ordered, start=1):
        depth_mm = need.target_depth_mm.value
        duration_s = need.duration_s

        if depth_mm > constraints.max_daily_mm:
            clamp_ratio = constraints.max_daily_mm / depth_mm
            depth_mm = constraints.max_daily_mm
            duration_s = round(duration_s * clamp_ratio)

        event = RecipeEvent(
            start_utc=current_time,
            duration_s=duration_s,
            target_mm=DepthMM(depth_mm),
            priority=priority,
        )
        events.append((need.zone_id, event))
        current_time = current_time + timedelta(seconds=duration_s)

    return events


__all__ = ["schedule_events"]

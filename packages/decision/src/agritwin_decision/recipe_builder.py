"""Assembles the final (unsigned) `Recipe` from a scheduled event list.

Signing stays `packages/api`'s job (`agritwin_core.recipe_signing`) — this
module's output is exactly the request body
`PUT /admin/parcels/{parcel_id}/recipe` already expects
(`packages/api/src/agritwin_api/routers/admin.py`), so no change is needed
there; this package is simply a new, non-manual producer of that body.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from agritwin_core.schema import (
    FallbackPolicy,
    Recipe,
    RecipeConfidence,
    RecipeConstraints,
    RecipeEvent,
    RecipeZone,
)

from agritwin_decision.policy import DEFAULT_POLICY, IrrigationPolicy
from agritwin_decision.zone_plan import ZoneIrrigationNeed


def build_recipe(
    *,
    parcel_id: str,
    recipe_id: str,
    issued_at: datetime,
    zone_events: list[tuple[str, RecipeEvent]],
    needs: list[ZoneIrrigationNeed],
    constraints: RecipeConstraints,
    policy: IrrigationPolicy = DEFAULT_POLICY,
) -> Recipe:
    """`needs` carries the per-zone `confidence` that produced
    `zone_events` (`scheduler.schedule_events`'s output has no confidence
    field of its own — `RecipeEvent` is the wire contract and stays exactly
    as specified in `docs/architecture.md` section 4, not extended for an
    internal bookkeeping need). The recipe's overall `confidence` is the
    worst case across zones: any zone reporting `"low"` makes the whole
    recipe `"low"`, since `docs/architecture.md` section 4 treats
    `confidence` as a single farmer-facing signal, not per-zone.
    """
    zones_by_id: dict[str, list[RecipeEvent]] = {}
    for zone_id, event in zone_events:
        zones_by_id.setdefault(zone_id, []).append(event)

    recipe_zones = [
        RecipeZone(zone_id=zone_id, events=events) for zone_id, events in zones_by_id.items()
    ]

    confidence = (
        RecipeConfidence.LOW
        if any(need.confidence == "low" for need in needs)
        else RecipeConfidence.NORMAL
    )

    return Recipe(
        recipe_id=recipe_id,
        parcel_id=parcel_id,
        issued_at=issued_at,
        valid_from=issued_at,
        valid_until=issued_at + timedelta(hours=policy.recipe_validity_hours),
        confidence=confidence,
        fallback_policy=FallbackPolicy.NO_IRRIGATION,
        zones=recipe_zones,
        constraints=constraints,
    )


__all__ = ["build_recipe"]

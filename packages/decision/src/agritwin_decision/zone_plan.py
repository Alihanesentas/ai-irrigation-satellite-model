"""Single-zone irrigation planning: `SoilState` + `Zone` + `IrrigationPolicy`
-> a concrete depth/duration, or nothing at all.

This is the only module that reads soil-physics *thresholds* (`raw_mm`,
`taw_mm`) — and it reads them from `SoilState`, never computes them, per
`CLAUDE.md` rule 3 ("decision engine never imports a concrete model class").
The only import from `agritwin_twin` anywhere in this package is
`interface.SoilState` — a data type, not a model.
"""

from __future__ import annotations

from dataclasses import dataclass

from agritwin_core.schema import Zone
from agritwin_core.units import DepthMM, depth_to_volume
from agritwin_twin.interface import SoilState

from agritwin_decision.policy import DEFAULT_POLICY, IrrigationPolicy


@dataclass(frozen=True, slots=True)
class ZoneIrrigationNeed:
    """One zone's computed irrigation need for today — `None` from
    `plan_zone_need` means no need at all, not a zero-length one
    (`CLAUDE.md` rule 6: silence over a fabricated zero-duration event)."""

    zone_id: str
    target_depth_mm: DepthMM
    duration_s: int
    urgency: float
    """`(Dr - trigger_threshold) / raw_mm` — how far past the irrigation
    trigger this zone already is, normalized by its own `RAW` so zones with
    different bucket sizes are compared fairly. Used by `scheduler.py` to
    order zones most-depleted-first."""
    confidence: str


def plan_zone_need(
    soil_state: SoilState, zone: Zone, policy: IrrigationPolicy = DEFAULT_POLICY
) -> ZoneIrrigationNeed | None:
    """Returns `None` when `soil_state.dr_mm` has not yet crossed
    `policy.trigger_at_raw_fraction * soil_state.raw_mm` — the "safe
    default is closed" case (`CLAUDE.md` rule 6). Otherwise returns the
    depth to apply (dampened under low confidence,
    `docs/architecture.md` section 4) and the duration that depth takes at
    the zone's nominal flow rate. `policy` is a frozen dataclass, so reusing
    the module-level `DEFAULT_POLICY` instance as the default argument is
    safe (no mutable-default pitfall).
    """
    dr = soil_state.dr_mm.value
    raw = soil_state.raw_mm.value
    trigger_threshold = policy.trigger_at_raw_fraction * raw

    if dr < trigger_threshold:
        return None

    refill_fraction = (
        policy.low_confidence_refill_fraction
        if soil_state.confidence == "low"
        else policy.target_refill_fraction
    )
    depth_mm = dr * refill_fraction
    if depth_mm <= 0:
        return None

    volume_l = depth_to_volume(DepthMM(depth_mm), zone.area_m2)
    duration_min = volume_l.value / zone.nominal_flow_l_min
    duration_s = round(duration_min * 60)

    urgency = (dr - trigger_threshold) / raw if raw > 0 else dr

    return ZoneIrrigationNeed(
        zone_id=zone.zone_id,
        target_depth_mm=DepthMM(depth_mm),
        duration_s=duration_s,
        urgency=urgency,
        confidence=soil_state.confidence,
    )


__all__ = ["ZoneIrrigationNeed", "plan_zone_need"]

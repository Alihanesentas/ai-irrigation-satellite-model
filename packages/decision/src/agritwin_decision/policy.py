"""Irrigation trigger/target policy — the tunable knobs of the decision
engine. See `docs/decisions/irrigation-trigger-policy.md` for the sourcing
and rationale behind each default; this module only encodes them.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IrrigationPolicy:
    trigger_at_raw_fraction: float = 1.0
    """Irrigate once `Dr >= trigger_at_raw_fraction * raw_mm`. 1.0 = FAO-56's
    own no-stress boundary (`docs/fao56-calculations.md` section 9.3: `Ks`
    starts falling below 1 exactly at `Dr > RAW`) — irrigating right at that
    line, not earlier or later, per
    `docs/decisions/irrigation-trigger-policy.md`."""

    target_refill_fraction: float = 1.0
    """Target `Dr` after irrigation, as a fraction of the way from the
    current `Dr` back to 0. 1.0 = full refill to field capacity."""

    low_confidence_refill_fraction: float = 0.6
    """Refill fraction used instead of `target_refill_fraction` when
    `SoilState.confidence == "low"` — a conservative plan, never zero.
    `docs/architecture.md` section 4: "confidence: low ... The decision
    engine already produced a conservative plan; the device does not
    reinterpret it" — this is that mechanism."""

    recipe_validity_hours: int = 48
    """`valid_until - valid_from` for a generated `Recipe`. Matches the
    "24-48 hour JSON recipe" language throughout `docs/architecture.md`."""


DEFAULT_POLICY = IrrigationPolicy()

__all__ = ["IrrigationPolicy", "DEFAULT_POLICY"]

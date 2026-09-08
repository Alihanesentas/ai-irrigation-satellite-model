# Irrigation trigger policy — first decision-engine slice

**Status:** Proposed

## Context

`docs/modules.md` names `packages/decision/` as the module that turns twin state into a recipe:
"Owns: Scheduling, water budget optimisation, recipe generation and validity windows... Must
degrade gracefully: when the twin reports low confidence, the recipe becomes conservative
rather than absent." `docs/delivery-plan.md` Phase 2 lists "Decision engine: soil water deficit
to recipe, under constraints" as a build item, without specifying the exact trigger rule,
refill target, or scheduling method — those are what this record settles for the first
implemented slice (`packages/decision/src/agritwin_decision/`).

This closes the loop end-to-end for the first time: `packages/twin`'s `SoilState` now has a
consumer, and that consumer's output was verified against the already-built
`packages/api`/`packages/simulator` (backend signs the produced recipe; the device simulator
polls, verifies, executes it, and correctly applies the `target_mm` early-abort).

## Decision

1. **Trigger:** irrigate once `Dr >= RAW` (FAO-56's own no-stress boundary — the same point
   `Ks` starts falling below 1, `docs/fao56-calculations.md` section 9.3). Not a fixed
   depth-based threshold or an earlier/later fraction of RAW.
2. **Target:** refill fully to `Dr = 0` (field capacity) by default; refill only 60% of the way
   when `SoilState.confidence == "low"` — never zero. This is the concrete mechanism behind
   `docs/architecture.md` section 4's "confidence: low ... the decision engine already produced
   a conservative plan."
3. **Multi-zone scheduling:** greedy, most-urgent-first (ranked by depletion past trigger,
   normalized by each zone's own RAW), sequential (one zone at a time), clamped to
   `RecipeConstraints.max_daily_mm` with duration scaled down proportionally.
4. **The decision engine reads `SoilState.raw_mm`/`taw_mm`, it never computes them.** Those
   fields were added to `SoilState` (additive) specifically so `packages/decision` never needs a
   crop or soil parameter, preserving `CLAUDE.md` rule 3.

## Rationale

**Why RAW as the trigger, not something more conservative or more permissive.** RAW is the
textbook FAO-56 boundary at which stress begins — triggering exactly there means the model
never lets the crop enter measurable stress under normal (non-low-confidence) operation, and
never irrigates before it's needed either. An earlier trigger (e.g. `0.5 * RAW`) has no basis in
either FAO-56 or this project's docs; it would be an invented safety margin dressed up as
physics.

**Why full refill by default.** Refilling only partway under normal confidence would mean the
system is quietly more conservative than its own stated confidence level implies — the
low-confidence dampening mechanism exists specifically so "conservative" is a distinct, visible
state, not blended into the default behaviour.

**Why greedy sequential scheduling, not `scipy.optimize`/`cvxpy`.** `docs/modules.md` names the
latter as the eventual stack, but there is no real multi-zone conflicting objective yet to
justify it — a single pilot parcel with a handful of zones and `max_concurrent_zones` typically
1 (single mainline valve) has nothing for a joint optimizer to trade off against. Reaching for
LP machinery now would be complexity without a problem, which `CLAUDE.md` rule 4 ("boring
technology wins") argues against by the same logic it applies to infrastructure choices. This
should be revisited once a real pilot parcel has enough zones/constraints for scheduling
conflicts to actually occur.

**Why `packages/decision` never computes RAW/TAW itself.** The alternative — giving the decision
engine its own copy of crop/soil parameters to compute thresholds — would duplicate exactly the
physics `packages/twin` already owns, and risks the two packages disagreeing about where the
stress boundary is. Reporting `raw_mm`/`taw_mm` on `SoilState` keeps "the twin computes physical
thresholds, the decision engine acts on them" as a clean, testable seam.

## Consequences

- A day with no zone past its trigger produces a recipe with an empty `zones[].events` list, not
  an error and not a fabricated no-op event — consistent with `plan_zone_need` returning `None`
  rather than a zero-duration `ZoneIrrigationNeed`.
- `max_daily_mm` clamping means a badly depleted zone may take multiple days to fully refill;
  v1 does not split a refill across a multi-day recipe — each day's planning run reassesses `Dr`
  fresh and schedules whatever is still needed.
- This policy has never been compared against a real agronomist's schedule (Gate 2's actual exit
  criterion) — it is a defensible FAO-56-grounded default, not a validated one. Expect to revise
  `trigger_at_raw_fraction`/`target_refill_fraction` once that comparison is possible.

## Rejected

- **A learned/ML-based irrigation trigger.** Explicitly prohibited —
  `CLAUDE.md`: "Do not make the irrigation decision a learned classifier. No ground-truth labels
  exist." Not reconsidered here.
- **A fixed depth applied regardless of `Ks`.** Rejected because it throws away the water-stress
  signal `packages/twin` already computes — the whole point of tracking `Dr`/`RAW`/`TAW` per
  zone is to make the trigger state-dependent, not a blind schedule.
- **A full `cvxpy` multi-zone joint optimizer for v1.** Rejected for now — see Rationale. Revisit
  once real multi-zone/multi-constraint conflicts exist to optimize against.

# packages/decision — Decision engine

Turns twin state into a 24-48 hour irrigation recipe. Consumes `SoilModel`
output through the protocol only — never imports a concrete model class
(`CLAUDE.md`). Full responsibility and boundaries: `docs/modules.md#decision-engine`.

**Status:** in progress — first slice. A rule-based water-budget planner is
implemented and verified end-to-end against `packages/api` and
`packages/simulator` (twin state → recipe → signed by the backend → executed
by the device simulator). Not yet Gate 2: that exit criterion needs real
parcels and an agronomist's schedule to compare against, which don't exist.
See `docs/decisions/irrigation-trigger-policy.md` for the policy this slice
implements and what's deliberately still missing.

## What's here

- `policy.py` — `IrrigationPolicy`: the trigger/target/safety-margin knobs
  (RAW-triggered, full-refill-by-default, dampened under low confidence).
- `zone_plan.py` — `plan_zone_need(soil_state, zone, policy)`: single-zone
  planning. Reads `SoilState.raw_mm`/`taw_mm` (thresholds the twin computes
  and reports) rather than any crop/soil parameter itself — this is what
  keeps the package soil-physics-free per `CLAUDE.md` rule 3. Returns `None`
  (not a zero-duration event) when no irrigation is needed — rule 6, safe
  default is closed.
- `scheduler.py` — `schedule_events(needs, constraints, start_at)`: greedy,
  most-urgent-first, sequential multi-zone scheduling; clamps to
  `RecipeConstraints.max_daily_mm`. Not a `scipy.optimize`/`cvxpy` joint
  optimizer yet — see the decision record for why.
- `recipe_builder.py` — `build_recipe(...)`: assembles an **unsigned**
  `agritwin_core.schema.Recipe`. Signing stays `packages/api`'s job
  (`PUT /admin/parcels/{parcel_id}/recipe` already expects exactly this
  shape — no backend change was needed to consume this package's output).

## Verified end-to-end

`BucketModel.step()` (an olive zone, Manisa) → `plan_zone_need` →
`schedule_events` → `build_recipe` → `PUT /admin/parcels/{id}/recipe`
(real `packages/api` instance, signs it) → `DeviceSimulator` (real
`packages/simulator`) polls, verifies the Ed25519 signature, arms,
irrigates, and stops early on `target_mm` reached — the full loop this
session's earlier work built, now with something other than a manually
fabricated recipe driving it.

## Running

```bash
cd packages/decision
uv sync
uv run pytest -q
```

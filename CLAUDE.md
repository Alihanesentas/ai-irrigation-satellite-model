# CLAUDE.md — Project Contract

Binding working rules for every AI assistant and developer touching this repo.
**Read `docs/decisions/` before writing code or making an architectural call.**

---

## What this is

An end-to-end agricultural telemetry and irrigation platform that uses **no physical soil
sensors**. Soil state is simulated from satellite and weather data as a digital twin of the
field, and field valves are driven autonomously from that twin.

Full picture: `docs/architecture.md` · Module boundaries: `docs/modules.md`

---

## Binding rules

1. **Do not write code that contradicts a decision record.** If a contradiction is needed,
   propose a revision to the record first, get approval, then implement.
2. **Do not close an open question by assumption.** Items in `docs/open-decisions.md` are
   undecided. If your code touches one, stop and ask.
3. **Physics code and product code live apart.** Model implementations under
   `packages/twin/` implement the `SoilModel` protocol. The decision engine never imports a
   concrete model class.
4. **Boring technology wins.** Kubernetes, microservices, message-queue architectures,
   GraphQL — none are added without a written reason. Default is one VPS + Docker Compose.
5. **Units are explicit.** Soil moisture is always volumetric (m3/m3). Water depth is mm.
   Time is UTC. Local-time conversion happens only in the edge layer, with an explicit offset.
6. **Safe default is closed.** On any code path that can actuate a valve, uncertainty must
   resolve to "do not irrigate". Never fail open.

---

## Prohibitions

Each links to the record that explains why.

- Do not build a Sentinel-1 GRD processing chain from scratch. Consume pre-built RTC products.
  -> `decisions/data-access-layer.md`
- Do not use ERA5-Land as forcing in the operational inference path. Publication lag is ~2-3
  months. -> `decisions/weather-forcing-split.md`
- Do not add post-hoc bias/offset correction to model output. It breaks mass conservation.
  -> `decisions/pooling-strategy.md`
- Do not train an independent model per parcel. Identifiability failure.
  -> `decisions/pooling-strategy.md`
- Do not solve hydrological columns at 10 m pixel level. Modelling finer than actuator
  granularity is waste. -> `decisions/spatial-analysis-unit.md`
- Do not make the irrigation decision a learned classifier. No ground-truth labels exist.
  -> `decisions/ml-layering.md`
- Do not store derived volume without raw pulse count and k-factor. -> `schemas.md`
- Do not apply wetted fraction inside `IRRIGATION_LOG`. Logs record fact; the twin
  interprets. -> `schemas.md`

Before proposing an alternative to any of the above, read `docs/superseded-decisions.md` —
it may already have been considered and rejected.

---

## Directory map

```
docs/decisions/       Architecture decision records — read these first
docs/architecture.md  Principles, data flow, cross-cutting concerns
docs/modules.md       The six modules: responsibilities, boundaries, stack
docs/open-decisions.md   Questions not yet settled
docs/superseded-decisions.md  Abandoned options and why — read before re-proposing one
docs/delivery-plan.md Phases, gates, tracks, risk register
docs/schemas.md       Concrete field definitions frozen at Gate 1
docs/cost-model.md    Cost model and unit economics
packages/core/        Shared schema: parcel, zone, units, constants
packages/etl/         Data plane — Dagster assets
packages/twin/        Digital twin — SoilModel protocol, bucket + PINN
packages/decision/    Decision engine — optimisation, recipe generation
packages/api/         Cloud backend — FastAPI
apps/web/             Farmer interface — Next.js PWA
firmware/             Edge node — ESP-IDF / Zephyr
experiments/          Phase 0 throwaway notebooks; production code must not import from here
```

---

## Current phase

**Phase 1 — telemetry and control plane.** See `docs/delivery-plan.md`.

No model, no hardware. A device simulator stands in for the field. The recipe contract,
telemetry schema and conformance suite are Gate 1 deliverables and freeze there.

The SAR feasibility spike runs as a parallel research track in `experiments/` and blocks
nothing in Phase 1 or 2.

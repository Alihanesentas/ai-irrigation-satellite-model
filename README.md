# AI Irrigation Satellite Model

An end-to-end agricultural telemetry and irrigation platform that uses **no physical soil
sensors**. Soil state is simulated from satellite and weather data as a digital twin of the
field, and field valves are driven autonomously from that twin.

**Status:** Phase 0 — feasibility. No production code under `packages/` until Phase 0 closes.

## Start here

- [`CLAUDE.md`](CLAUDE.md) — binding project contract and working rules
- [`docs/architecture.md`](docs/architecture.md) — principles, data flow, cross-cutting concerns
- [`docs/modules.md`](docs/modules.md) — the six modules: responsibilities, boundaries, stack
- [`docs/decisions/`](docs/decisions/) — architecture decision records, read before writing code
- [`docs/open-decisions.md`](docs/open-decisions.md) — questions not yet settled
- [`docs/cost-model.md`](docs/cost-model.md) — cost model and unit economics

## Layout

```
docs/decisions/       Architecture decision records
docs/architecture.md  Principles, data flow, cross-cutting concerns
docs/modules.md       The six modules: responsibilities, boundaries, stack
docs/open-decisions.md   Questions not yet settled
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

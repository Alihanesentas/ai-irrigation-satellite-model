# packages/core

Shared schema: parcel, zone, units, constants. Consumed by every other package —
no package depends downward into `etl`, `twin`, `decision`, or `api`.

**Status:** not started — see `docs/modules.md` and `docs/decisions/development-phases.md`.
No production code until Phase 0 closes (`CLAUDE.md`).

**Update:** `docs/decisions/development-phases.md` is superseded by
`docs/delivery-plan.md`. The project is now in Phase 1 (telemetry and control
plane), and a module skeleton exists under `src/agritwin_core/` — see
`units.py`, `schema.py`, `constants.py`. All are stubs/typed contracts, not a
working implementation.

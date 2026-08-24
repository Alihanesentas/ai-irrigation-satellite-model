# packages/etl — Data plane

Reduces raw satellite and weather inputs into the canonical zone-day table.
Full responsibility and boundaries: `docs/modules.md#data-plane`.

**Status:** blocked on Phase 0 (`docs/decisions/development-phases.md`).
No production code until Phase 0 closes (`CLAUDE.md`).

**Update:** `docs/decisions/development-phases.md` is superseded by
`docs/delivery-plan.md`. The project is now in Phase 1, and a module skeleton
exists under `src/agritwin_etl/` — `config.py` (central secrets
abstraction — no credentials filled in yet), `sources/` (one stub client per
data source, all raising `NotImplementedError`), `assets/` (Dagster asset
stubs at zone-day granularity), and `definitions.py`/`workspace.yaml`. No
credentials exist yet and nothing here fetches real data.

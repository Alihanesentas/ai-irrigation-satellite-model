# packages/decision — Decision engine

Turns twin state into a 24-48 hour irrigation recipe. Consumes `SoilModel`
output through the protocol only — never imports a concrete model class
(`CLAUDE.md`). Full responsibility and boundaries: `docs/modules.md#decision-engine`.

**Status:** not started. Per `docs/delivery-plan.md`, the Decision track runs Phase 2-3 and
gates on the Platform contract (recipe schema, telemetry schema) being frozen at Gate 1 — not
on Phase 0 (that rule was superseded, see `docs/superseded-decisions.md`).

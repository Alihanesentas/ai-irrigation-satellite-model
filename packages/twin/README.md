# packages/twin — Digital twin

Estimates theta(z,t) and its uncertainty via the `SoilModel` protocol
(`interface.py`), implemented by `models/bucket.py` (Phase 1) and
`models/pinn.py` (Phase 2). Never decides when to irrigate.
Full responsibility and boundaries: `docs/modules.md#digital-twin`.

**Status:** not started. `docs/decisions/development-phases.md` is superseded by
`docs/delivery-plan.md`: the bucket-model `SoilModel` implementation starts in Phase 2 (gated
on the Platform contract frozen at Gate 1); the PINN implementation starts in Phase 3, gated on
Gate 2 and a positive outcome from the parallel SAR feasibility research track
(`experiments/`), which itself blocks nothing in Phase 1-2.

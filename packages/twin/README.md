# packages/twin — Digital twin

Estimates theta(z,t) and its uncertainty via the `SoilModel` protocol
(`interface.py`), implemented by `models/bucket.py` (Phase 1/2, and the
permanent L2/L3 fallback — `docs/architecture.md#8-degradation-ladder`) and,
later, `models/pinn.py` (Phase 3). Never decides when to irrigate.
Full responsibility and boundaries: `docs/modules.md#digital-twin`.

**Status:** in progress. The `SoilModel` protocol and the FAO-56 dual-Kc
bucket model are implemented ahead of `docs/delivery-plan.md`'s nominal
Phase 2 start, since both are crop-agnostic and blocked on no open decision
— see `docs/decisions/crop-parameterization-manisa.md`. The PINN
(`models/pinn.py`) still starts in Phase 3, gated on Gate 2 and a positive
outcome from the parallel SAR feasibility research track (`experiments/`).

## What's here

- `interface.py` — the `SoilModel` protocol, `DailyForcing`, `SoilState`.
  Written first per `docs/modules.md`'s instruction; the decision engine
  will depend on this protocol only, never a concrete model class
  (`CLAUDE.md` rule 3).
- `meteorology.py` — FAO-56 Penman-Monteith ET0 and every input it needs
  (`docs/fao56-calculations.md` sections 1-7), term for term.
- `crops.py` — the per-crop parameter layer: `CropParameters`, plus two
  Manisa presets, `OLIVE_MANISA` and `GRAPE_MANISA`
  (`docs/decisions/crop-parameterization-manisa.md`).
- `soils.py` — per-texture soil hydraulic parameters (FAO-56 field
  capacity/wilting point, and the van Genuchten-Mualem closure from
  `docs/fao56-calculations.md` section 11.2), with a `CLAY_LOAM_MANISA`
  preset.
- `percolation.py` — van Genuchten K(θ) unsaturated hydraulic conductivity
  — the "flow coefficient" governing how fast water actually reaches the
  root zone versus draining away, used as an alternative to FAO-56's
  instant-drain deep percolation assumption.
- `models/bucket.py` — the FAO-56 dual-Kc bucket model itself
  (`docs/fao56-calculations.md` sections 8-9), implementing `SoilModel`.
  Supports both percolation modes (`BucketConfig.percolation_mode`) for
  direct comparison.

## Benchmark

`experiments/notebooks/05_fao56_bucket_benchmark.ipynb` runs both crops
against real Manisa 2023 weather (Open-Meteo archive API, no credentials
needed) and cross-validates this package's ET0 against Open-Meteo's own
independently-computed FAO-56 ET0 (R²=0.99 over the full year at last run).
It imports this package directly — production code and the notebook never
duplicate the equations, per `CLAUDE.md`'s "production code under
`packages/` must never import from `experiments/`" (the dependency here
only ever runs the other way).

## Running

```bash
cd packages/twin
uv sync
uv run pytest -q
```

# experiments

Phase 0 feasibility spike: does S1 carry a usable moisture signal for the
target crop in the target region? Throwaway code — unrestricted, does not
need to be clean. Production code under `packages/` must never import from
here (`CLAUDE.md`).

Scope and exit criteria: `docs/decisions/development-phases.md`.

## Notebooks

- `01_data_explorer.ipynb` - `04_validation.ipynb` — Phase 0 SAR feasibility
  work, synthetic data (no data-source credentials configured yet).
- `05_fao56_bucket_benchmark.ipynb` — benchmarks `packages/twin`'s FAO-56
  dual-Kc bucket model (olive & grape, Manisa) against **real** weather data
  (Open-Meteo archive API, no credentials required) and an independent ET0
  reference. Unlike 01-04, this one imports the production `agritwin_twin`
  package directly rather than reimplementing anything — see
  `packages/twin/README.md`.

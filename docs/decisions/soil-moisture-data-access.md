# Soil moisture data access

**Status:** Accepted

## Context

`data-access-layer.md` covers Sentinel-1, Sentinel-2, weather, and SoilGrids. It does not
cover soil moisture as a directly-sourced product — SMAP and ISMN were adopted during
telemetry-pipeline planning but never recorded as a decision. The twin (`packages/twin/`)
needs a soil moisture signal to assimilate against, distinct from the SAR backscatter it
estimates state from (`observation-operator.md`).

## Decision

**Both SMAP and ISMN, as two independent pipelines.** SMAP (NASA, satellite, gridded, 9 km,
daily) is the primary assimilation input. ISMN (in-situ ground stations, point measurements)
is not folded into the same pipeline — it runs as a second, independent path used to
cross-validate SMAP over any AOI where an ISMN station falls inside or near the pilot region.

## Rationale

A single remote-sensing soil moisture product has no independent check on it — if SMAP has a
regional bias or a retrieval failure mode specific to the pilot area's soil texture or land
cover, nothing in a single-pipeline design would surface it. Two structurally independent
pipelines (different instruments, different physics, different failure modes) give a
correlation/RMSE/bias check that a single source cannot self-report.

This mirrors the existing `weather-forcing-split.md` pattern: two lines for the same
underlying quantity, kept structurally separate rather than merged, because merging early
would hide exactly the discrepancy the second source exists to catch.

## Consequences

- Two more external dependencies and SLAs, alongside the four already tracked
  (`data-access-layer.md`, `landsat-data-access.md`).
- SMAP and ISMN outputs must never be silently merged into one column/table — same rule as
  the operational/archive weather split. Cross-validation happens in an explicit comparison
  step, not by treating them as interchangeable inputs.
- ISMN's point measurements do not cover every zone; where no station exists nearby,
  cross-validation cannot run for that zone and this must be visible in output metadata, not
  silently skipped.
- `smap_zone_day` and `ismn_zone_day` are separate Dagster assets at zone-day granularity
  (`spatial-analysis-unit.md`), matching the pattern used for every other source.
- Neither SMAP nor ISMN is the twin's state estimate — both are observations the twin
  assimilates against (`observation-operator.md`), same status as SAR backscatter.

## Rejected

- **SMAP only, no cross-validation source** — cheaper, but removes the only independent check
  on retrieval quality; rejected given the safety-critical nature of the downstream valve
  actuation (`CLAUDE.md` rule 6: uncertainty must resolve to "do not irrigate", and an
  unverified soil moisture bias directly threatens that guarantee).
- **Merge SMAP and ISMN into one blended soil-moisture column** — discards the ability to
  detect disagreement between the two; same reasoning as the rejected ERA5/operational
  weather merge in `weather-forcing-split.md`.

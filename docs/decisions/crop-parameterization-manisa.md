# Crop parameterization — olive and grape, Manisa pilot

**Status:** Proposed

## Context

`docs/modules.md` names `packages/twin/models/bucket.py` as the FAO-56 dual crop coefficient
water balance implementation, and `docs/fao56-calculations.md` sections 7-9 specify every
equation it needs. Neither document supplies the per-crop numeric parameters (`Kcb`,
root depth, depletion fraction, growth-stage timing) or the per-region soil hydraulic
parameters the equations are evaluated against — those are config, not architecture, but they
still need a single recorded source so a future implementer doesn't re-derive or silently
change them. This record is that source for `packages/twin/src/agritwin_twin/crops.py` and
`soils.py`.

Two crops were selected for this pilot parameterization — **olive (zeytin)** and **table/raisin
grape, specifically sultana (üzüm)** — because they are Manisa's two dominant tree/vine crops
and, per `docs/open-decisions.md`'s "Target cropping pattern" entry, represent the two ends of
the still-open annual-vs-perennial question (both are perennial here, but with materially
different phenology: olive evergreen, grape deciduous). This record does not close that open
decision — it only supplies parameters usable for benchmarking regardless of how it resolves.

## Decision

Use FAO-56 (Allen et al. 1998) Table 12 and Table 22 published values for **olives (40-60%
ground cover)** and **grapes — table/raisin** (not the wine-grape row — Manisa's dominant
variety, Sultaniye, is a table/raisin type), with two explicit, documented deviations from the
raw table values:

1. **Olive `Kcb_mid`/`Kcb_end` scaled by 0.82.** A Mediterranean eddy-covariance olive-orchard
   study found the raw FAO-56 table value overestimates actual measured ET by roughly 18% under
   Mediterranean conditions. Applied as a multiplicative correction, kept visible alongside the
   unadjusted curve in the benchmark notebook rather than silently replacing the table value.
2. **Growth-stage day-lengths are constructed, not tabulated.** FAO-56 Table 11 only defines
   initial/development/mid/late stage lengths for annual field crops; neither olive nor grape is
   one. Season timing here (olive: ~May-Oct fruit-set-to-oil-accumulation window, evergreen
   canopy holds `Kcb_end` outside that window; grape: ~March-Sept bud-break-to-harvest, dormant
   `Kcb≈0` outside it) is built from secondary Mediterranean-orchard literature, flagged as the
   lowest-confidence part of this parameterization.

Soil hydraulics use a single **clay loam** preset (`soils.py: CLAY_LOAM_MANISA`), identified in
Manisa vineyard-soil-survey literature as representative of the region, with both the FAO-56
`theta_FC`/`theta_WP` pair and the van Genuchten-Mualem closure parameters
(`docs/fao56-calculations.md` section 11.2) needed by the model's alternate percolation mode.

## Rationale

**Why not wait for real SoilGrids/S2 data before writing any crop parameters.**
`packages/etl/src/agritwin_etl/sources/soilgrids.py` and `sentinel2.py` are still
`NotImplementedError` stubs — there is no near-term real data to parametrize from. Literature
defaults, explicitly labeled as needing local calibration, let the bucket model (and the
benchmark notebook validating it) exist and be exercised now, without pretending they are
Manisa-measured. Every field in `crops.py`/`soils.py` that came from a table lookup carries an
inline citation; every field that was constructed rather than looked up says so.

**Why `"Proposed"` and not `"Accepted"`.** Unlike the architecture-level decisions in this
directory, these are literature-typical numeric defaults expected to be superseded by real
calibration (S2 NDVI phenology, real soil survey, real yield/soil-moisture ground truth) as
soon as that data exists — this status reflects "in use, not yet validated against real Manisa
field data," not an open disagreement about the modeling approach itself.

## Consequences

- `packages/twin`'s benchmark notebook (`experiments/notebooks/05_fao56_bucket_benchmark.ipynb`)
  is reproducible against these exact values; changing a preset in `crops.py`/`soils.py`
  changes the notebook's next run, keeping the two in sync by construction (the notebook imports
  the production module, it does not duplicate the parameters).
- The olive local-adjustment factor is a single global multiplier sourced from one external
  study, not a Manisa fit. It should be one of the first things replaced once real applied-water
  and satellite data (`docs/decisions/applied-water-measurement.md`'s self-calibration loop)
  exists for Manisa olive parcels specifically.
- Growth-stage timing being constructed rather than tabulated means the `Kcb` seasonal curve is
  the single least-trustworthy input to any ETc/irrigation-need number this model currently
  produces — more so than the ET0 weather-driven side, which validates cleanly against an
  independent reference (see the benchmark notebook, section 2).

## Rejected

- **Wine-grape FAO-56 row instead of table/raisin.** Rejected because Manisa's dominant grape
  variety (Sultaniye/sultana) is a table-and-raisin type, not a wine variety; using the wine row
  would misrepresent the actual regional crop even though both rows come from the same FAO-56
  table.
- **A single generic "Kc" (not dual Kcb+Ke) for a faster first pass.** Rejected because
  `docs/modules.md` and `docs/fao56-calculations.md` section 8.2 both specify the dual-Kc form
  as what this system uses — the single-Kc form cannot represent a wetting event's short-term
  soil evaporation spike independent of crop stage, which matters directly for how applied
  irrigation shows up in the water balance.
- **Waiting for real SoilGrids texture data before picking a soil preset.** Rejected — no
  timeline exists for that pipeline; a literature-typical clay loam default, clearly labeled,
  unblocks the bucket model and benchmark now.

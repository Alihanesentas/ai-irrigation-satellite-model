# Landsat data access

**Status:** Accepted

## Context

`data-access-layer.md` covers Sentinel-1, Sentinel-2, weather, and SoilGrids. It does not
cover long historical time-depth: Sentinel-2 only reaches back to 2015-2017 depending on tile,
and Sentinel-1 RTC archives are similarly shallow. Calibrating parcel adaptation and any
backbone training benefits from a longer, consistent optical record.

## Decision

**Landsat-8/9, accessed via STAC.** Microsoft Planetary Computer STAC API is primary — no
registration friction, well-documented, free. USGS M2M (`https://m2m.cr.usgs.gov`) is the
fallback if Planetary Computer coverage or licensing terms become a blocker.

## Rationale

Landsat's 30 m resolution and 16-day revisit make it unsuitable for the operational
near-real-time path — Sentinel-1 and Sentinel-2 already cover that at 10-20 m with faster
revisit. Landsat's role is different: historical depth (Landsat-8 archive back to 2013) for
calibration and trend/backbone training, not day-to-day inference.

## Consequences

- A fourth external dependency and SLA, alongside the three already listed in
  `data-access-layer.md`.
- Adds a `landsat_zone_day` asset at the same zone-day granularity as the other sources, per
  `spatial-analysis-unit.md`.
- Not part of the operational inference path — the same separation principle as
  `weather-forcing-split.md` applies: historical-depth sources feed training, not live
  decisions.

## Rejected

- **USGS M2M as primary** — heavier registration and auth flow than Planetary Computer for
  equivalent data. Kept as fallback only.

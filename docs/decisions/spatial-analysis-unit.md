# Spatial analysis unit

**Status:** Accepted

## Context

The spatial unit at which the hydrological column is solved drives cloud cost by two to three
orders of magnitude.

## Decision

**Management zones.** k-means over multi-year NDVI plus SoilGrids gives 2-4 zones per parcel.
One 1D Richards column per zone.

## Rationale

The irrigation valve already operates at zone level. **Modelling finer than actuator
granularity means paying for resolution that cannot be used.**

A single parcel average, on the other hand, discards within-field soil and slope
heterogeneity entirely — a real information loss on the sloped, mixed-profile parcels typical
of the region.

## Consequences

- Canonical ETL output granularity is **zone-day**. The feature store materialises there,
  not at raw scene level.
- Zone definitions refresh annually and stay fixed within a season, otherwise the time series
  breaks.
- Roughly 3x the cost of a parcel-average approach.

## Rejected

- **Parcel average** — cheapest, but heterogeneity loss is unacceptable.
- **Full 10 m raster** — scientifically richest, operationally pointless.

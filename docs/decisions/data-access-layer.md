# Data access layer

**Status:** Accepted

## Context

Four sources are required: Sentinel-1 (SAR), Sentinel-2 (optical), weather, SoilGrids. Each
has several access routes, trading engineering effort against cost and lock-in.

## Decision

**Hybrid access.**

- Sentinel-2 L2A -> Copernicus Data Space (openEO / Sentinel Hub)
- Sentinel-1 -> **pre-built RTC (Radiometrically Terrain Corrected) gamma0 products**
- Weather -> separate path, see `weather-forcing-split.md`
- SoilGrids -> static one-off download

## Rationale

**S1 GRD is not processed from scratch.** The chain is heavy: orbit correction, thermal noise
removal, calibration, terrain flattening, speckle filtering, geocoding. A pre-built RTC
product eliminates all of it.

**Terrain flattening is not negotiable.** The Aegean and Mediterranean countryside is
uneven. Without terrain flattening the moisture signal in backscatter is lost in slope
shadow. A layover/shadow mask is equally mandatory.

## Consequences

- Three dependencies, three SLAs. Each needs its own error handling and cache.
- Provider quotas and pricing change; verify current terms before integrating.

## Rejected

- **Google Earth Engine** — fastest prototype, but commercial licence cost, vendor lock-in,
  and a poor fit for heavy tensor inference.
- **Pure STAC + COG for everything** — cheapest at scale, highest upfront engineering. Kept
  open as a future migration path.

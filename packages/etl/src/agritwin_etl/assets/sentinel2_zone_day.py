"""Sentinel-2 L2A optical indices (NDVI etc.) reduced to zone-day granularity.

Governed by docs/decisions/data-access-layer.md (Copernicus Data Space) and
docs/decisions/spatial-analysis-unit.md (zone-day canonical granularity).
Cloud/gap handling happens here: a cloudy scene is unusable and gets filled in
later (this is exactly the routine-recomputation pattern that motivated
choosing Dagster — see docs/decisions/orchestration.md).
"""

from __future__ import annotations

import dagster as dg

zone_day_partitions = dg.DailyPartitionsDefinition(start_date="2024-01-01")


@dg.asset(
    partitions_def=zone_day_partitions,
    group_name="satellite",
    description="Sentinel-2 L2A NDVI/vegetation indices, zone-averaged per day, cloud-masked.",
)
def sentinel2_zone_day(context: dg.AssetExecutionContext) -> None:
    """One row per (zone, day): NDVI (and other vegetation indices as needed
    by packages/twin's WCM vegetation correction) plus a usable-pixel
    fraction after applying the L2A scene classification cloud mask.

    A day with insufficient usable pixels (per a threshold set at
    implementation time) should materialize as null/low-confidence rather
    than a fabricated value — do not interpolate silently at this layer.
    """
    raise NotImplementedError(
        "sentinel2_zone_day: pending Sentinel2Client implementation and "
        "zone geometry source."
    )

"""Landsat-8/9 optical reduced to zone-day granularity — long-baseline
calibration reference.

NOTE: no formal decision record exists yet for Landsat access
(docs/decisions/landsat-data-access.md is pending — see
agritwin_etl.sources.landsat docstring). This asset is wired into the graph
now so downstream consumers (feature_store_zone_day) have a stable
dependency to declare against; it will raise until that record lands and
LandsatClient is implemented.
"""

from __future__ import annotations

import dagster as dg

zone_day_partitions = dg.DailyPartitionsDefinition(start_date="2024-01-01")


@dg.asset(
    partitions_def=zone_day_partitions,
    group_name="satellite",
    description="Landsat-8/9 surface reflectance indices, zone-averaged per day (calibration reference).",
)
def landsat_zone_day(context: dg.AssetExecutionContext) -> None:
    """One row per (zone, day): Landsat-derived NDVI (or equivalent index),
    used to cross-check the Sentinel-2 series over the long baseline Landsat
    provides, not as a primary operational input.
    """
    raise NotImplementedError(
        "landsat_zone_day: pending docs/decisions/landsat-data-access.md and "
        "LandsatClient implementation."
    )

"""Sentinel-1 RTC backscatter reduced to zone-day granularity.

Governed by docs/decisions/data-access-layer.md (pre-built RTC gamma0 only)
and docs/decisions/spatial-analysis-unit.md (canonical output granularity is
zone-day, not raw scene — "materialise there, not at raw scene level").
"""

from __future__ import annotations

import dagster as dg

zone_day_partitions = dg.DailyPartitionsDefinition(start_date="2024-01-01")


@dg.asset(
    partitions_def=zone_day_partitions,
    group_name="satellite",
    description="Sentinel-1 RTC gamma0 backscatter (VV/VH), zone-averaged per day.",
)
def sentinel1_zone_day(context: dg.AssetExecutionContext) -> None:
    """One row per (zone, day): terrain-flattened gamma0 backscatter stats
    (mean, std within zone) plus layover/shadow mask coverage fraction.

    Fans in from agritwin_etl.sources.sentinel1.Sentinel1RTCClient across all
    RTC scenes whose acquisition date falls on this partition's day.
    """
    raise NotImplementedError(
        "sentinel1_zone_day: pending Sentinel1RTCClient implementation and "
        "zone geometry source."
    )

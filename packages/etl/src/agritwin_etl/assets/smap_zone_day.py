"""SMAP soil moisture reduced to zone-day granularity — primary soil moisture
assimilation input.

See agritwin_etl.sources.smap for the source client. Consumed by
packages/twin's assimilation step, not by the decision engine directly (the
decision engine only ever sees twin output through the SoilModel protocol —
see docs/modules.md#decision-engine).
"""

from __future__ import annotations

import dagster as dg

zone_day_partitions = dg.DailyPartitionsDefinition(start_date="2024-01-01")


@dg.asset(
    partitions_def=zone_day_partitions,
    group_name="soil_moisture",
    description="SMAP volumetric soil moisture (m3/m3), zone-averaged per day.",
)
def smap_zone_day(context: dg.AssetExecutionContext) -> None:
    """One row per (zone, day): SMAP volumetric moisture retrieval
    zone-averaged from the 9km grid, with retrieval quality flag carried
    through (not silently dropped on low quality — the twin's assimilation
    step needs to see it).
    """
    raise NotImplementedError(
        "smap_zone_day: pending SMAPClient implementation and zone geometry "
        "source."
    )

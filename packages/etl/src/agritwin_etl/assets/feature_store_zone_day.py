"""Canonical zone-day feature store — the single materialized output of the
data plane, matching the structure implied by docs/schemas.md and consumed
by packages/twin.

Per docs/decisions/spatial-analysis-unit.md: "Canonical ETL output granularity
is zone-day. The feature store materialises there, not at raw scene level."
Per docs/modules.md#data-plane: this is the boundary — the data plane "does
NOT own any model, prediction, or decision."

Design note: this asset depends on the OPERATIONAL weather line
(weather_operational_zone_day), not the archive line
(weather_archive_zone_day). weather_archive_zone_day has a different
partitions_def (start 2017-01-01 vs 2024-01-01 for the other zone-day assets)
and is training-only per docs/decisions/weather-forcing-split.md — mixing it
into this live feature store would both violate that record and create a
Dagster partition-mapping mismatch. A separate downstream asset for the
training dataset (joining weather_archive_zone_day against the same
satellite/soil-moisture assets) belongs in packages/twin's training pipeline,
not here.
"""

from __future__ import annotations

import dagster as dg

from agritwin_etl.assets.ismn_zone_day import ismn_zone_day
from agritwin_etl.assets.landsat_zone_day import landsat_zone_day
from agritwin_etl.assets.sentinel1_zone_day import sentinel1_zone_day
from agritwin_etl.assets.sentinel2_zone_day import sentinel2_zone_day
from agritwin_etl.assets.smap_zone_day import smap_zone_day
from agritwin_etl.assets.weather_operational_zone_day import weather_operational_zone_day

zone_day_partitions = dg.DailyPartitionsDefinition(start_date="2024-01-01")


@dg.asset(
    partitions_def=zone_day_partitions,
    group_name="feature_store",
    description="Canonical zone-day feature table: satellite + soil moisture + operational weather, joined.",
    deps=[
        sentinel1_zone_day,
        sentinel2_zone_day,
        landsat_zone_day,
        smap_zone_day,
        ismn_zone_day,
        weather_operational_zone_day,
    ],
)
def feature_store_zone_day(context: dg.AssetExecutionContext) -> None:
    """One row per (zone, day): the join of all upstream zone-day assets for
    this partition date. This is what packages/twin reads — it never reads
    the individual source assets directly (see docs/modules.md's
    twin-vs-decision-engine boundary note: keeping a single consumption point
    here is the data-plane equivalent of that same discipline).

    Column set should mirror docs/schemas.md's data-plane-relevant fields;
    exact schema TBD alongside packages/core.schema.Zone once real data
    starts flowing (this stub intentionally does not lock the column list to
    avoid drifting ahead of docs/schemas.md, which is a frozen Gate 1
    document — additive changes only).
    """
    raise NotImplementedError(
        "feature_store_zone_day: pending all upstream source client "
        "implementations and a persistence target (TimescaleDB, per project "
        "decision)."
    )

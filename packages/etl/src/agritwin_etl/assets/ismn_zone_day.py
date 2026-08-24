"""ISMN in-situ soil moisture reduced to zone-day granularity — SMAP
cross-validation pipeline, not a primary input.

A separate pipeline from smap_zone_day by design (project decision: run two
independent pipelines so one can validate the other, rather than merging them
at the source). Expect nulls for most zone-days — ISMN station coverage is
sparse and this asset should not be treated as gap-free.
"""

from __future__ import annotations

import dagster as dg

zone_day_partitions = dg.DailyPartitionsDefinition(start_date="2024-01-01")


@dg.asset(
    partitions_def=zone_day_partitions,
    group_name="soil_moisture",
    description="ISMN in-situ station soil moisture (m3/m3) near each zone, per day — validation only.",
)
def ismn_zone_day(context: dg.AssetExecutionContext) -> None:
    """One row per (zone, day) where a nearby ISMN station has data;
    otherwise absent (not a null placeholder row — sparse coverage is
    structural, not a data-quality defect to paper over).

    This asset is consumed by a validation/QA notebook or job that compares
    it against smap_zone_day, not by the twin directly.
    """
    raise NotImplementedError(
        "ismn_zone_day: pending ISMNClient implementation and zone geometry "
        "source."
    )

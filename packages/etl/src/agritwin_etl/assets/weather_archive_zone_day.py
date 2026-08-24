"""Archive weather forcing, zone-day granularity — training data ONLY.

Governed by docs/decisions/weather-forcing-split.md: this asset is the
ARCHIVE line (ERA5-Land, 2017-present, homogeneous). It feeds packages/twin
training and retrospective calibration exclusively.

**This asset's output must never be joined into an operational-path table.**
The domain shift this creates between training and inference distributions is
a tracked open item — see docs/open-decisions.md — not yet remedied. Do not
"fix" the gap between this asset and weather_operational_zone_day by merging
them; that is the prohibited shortcut the decision record calls out.
"""

from __future__ import annotations

import dagster as dg

zone_day_partitions = dg.DailyPartitionsDefinition(start_date="2017-01-01")


@dg.asset(
    partitions_def=zone_day_partitions,
    group_name="weather",
    description="Archive (ERA5-Land) daily weather aggregates per zone, training/calibration use only.",
)
def weather_archive_zone_day(context: dg.AssetExecutionContext) -> None:
    """One row per (zone, day) back to 2017: daily-aggregated ERA5-Land
    reanalysis variables, sourced from
    agritwin_etl.sources.weather_era5.ERA5LandClient exclusively.

    Partition start date (2017-01-01) reflects ERA5-Land's homogeneous
    coverage window per docs/decisions/weather-forcing-split.md, distinct
    from the 2024-01-01 default used by the other zone-day assets.
    """
    raise NotImplementedError(
        "weather_archive_zone_day: pending ERA5LandClient implementation and "
        "zone centroid coordinates."
    )

"""Operational weather forcing, zone-day granularity — feeds daily ET0 /
recipe generation.

Governed by docs/decisions/weather-forcing-split.md: this asset is the
OPERATIONAL line (Open-Meteo). It must never import
agritwin_etl.sources.weather_era5 — that module is the archive line, kept
strictly separate. This asset is the only legitimate upstream input for
recipe-generation-facing ET0 computation.
"""

from __future__ import annotations

import dagster as dg

zone_day_partitions = dg.DailyPartitionsDefinition(start_date="2024-01-01")


@dg.asset(
    partitions_def=zone_day_partitions,
    group_name="weather",
    description="Operational (Open-Meteo) daily weather aggregates per zone: temp, humidity, wind, radiation.",
)
def weather_operational_zone_day(context: dg.AssetExecutionContext) -> None:
    """One row per (zone, day): daily-aggregated meteorological inputs
    (Tmax, Tmin, RH, wind speed at 2m, solar radiation) sufficient for
    FAO-56 Penman-Monteith ET0 (see docs/fao56-calculations.md), sourced from
    agritwin_etl.sources.weather_openmeteo.OpenMeteoClient exclusively.
    """
    raise NotImplementedError(
        "weather_operational_zone_day: pending OpenMeteoClient implementation "
        "and zone centroid coordinates."
    )

"""ERA5-Land client — ARCHIVE / TRAINING forcing line ONLY.

MUST NOT be used in the operational inference path — see
docs/decisions/weather-forcing-split.md. This client is for packages/etl
training-data assets only (see weather_archive_zone_day.py in
agritwin_etl.assets). Importing this module into anything on the operational
recipe-generation path is prohibited and is checked in code review, per that
decision record.

Why the split exists: ERA5-Land has a publication lag of roughly 2-3 months,
so it cannot serve a 24-48h irrigation recipe. It IS used to build a
consistent, homogeneous training archive back to 2017 for the twin (PINN) —
see docs/decisions/weather-forcing-split.md "Consequences" for the resulting
train/inference domain-shift risk, which is an open item in
docs/open-decisions.md, not yet remedied.
"""

from __future__ import annotations

from datetime import date

from agritwin_etl.config import Settings


class ERA5LandClient:
    """Fetches ERA5-Land reanalysis data via the Copernicus Climate Data
    Store (CDS) API for the archive/training forcing line.

    Requires `Settings.copernicus_cds_api_key`.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch_reanalysis(
        self, zone_geometry_wkt: str, start_date: date, end_date: date
    ) -> None:
        """Fetch ERA5-Land hourly reanalysis variables (2m temperature,
        dewpoint, wind components, solar radiation) intersecting
        `zone_geometry_wkt` between `start_date` and `end_date`.

        Returns (once implemented): hourly meteorological series for the
        training archive. NEVER call this for a date within the operational
        24-48h recipe window — the 2-3 month publication lag makes that data
        unavailable, not just stale.
        """
        raise NotImplementedError(
            "ERA5LandClient.fetch_reanalysis: pending Copernicus CDS API key "
            "(Settings.copernicus_cds_api_key)."
        )

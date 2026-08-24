"""Landsat-8/9 client — long-history optical reference / calibration source.

NOTE: unlike Sentinel-1/2, Landsat has NO formal entry in
docs/decisions/data-access-layer.md yet. Per project decision, all three
optical/SAR sources (S1, S2, Landsat) are wanted; a decision record for the
Landsat access route is pending at docs/decisions/landsat-data-access.md and
should be written before this client is implemented for real — it is a stub
so the asset graph can be wired now without blocking on that record.

Two STAC-based candidate routes, not yet chosen:
- Microsoft Planetary Computer's Landsat Collection 2 STAC (no credential
  needed for read access at time of writing, but rate-limited).
- USGS M2M API (requires `Settings.usgs_m2m_username` /
  `Settings.usgs_m2m_token`).
"""

from __future__ import annotations

from datetime import date

from agritwin_etl.config import Settings


class LandsatClient:
    """Fetches Landsat-8/9 Collection 2 surface reflectance scenes for a
    zone/date range. Access route (Planetary Computer vs USGS M2M) undecided
    — see module docstring.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch_scenes(
        self, zone_geometry_wkt: str, start_date: date, end_date: date
    ) -> None:
        """Fetch Landsat scenes intersecting `zone_geometry_wkt` between
        `start_date` and `end_date`.

        Returns (once implemented): scene references for long-baseline
        optical calibration against the Sentinel-2 time series.
        """
        raise NotImplementedError(
            "LandsatClient.fetch_scenes: pending "
            "docs/decisions/landsat-data-access.md (route not yet chosen "
            "between Microsoft Planetary Computer and USGS M2M)."
        )

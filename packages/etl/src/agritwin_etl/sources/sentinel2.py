"""Sentinel-2 L2A client — Copernicus Data Space Ecosystem (openEO / Sentinel Hub).

Per docs/decisions/data-access-layer.md: S2 L2A via Copernicus Data Space
(openEO or Sentinel Hub API), not raw L1C reprocessing. Used for NDVI /
vegetation-index features (optical, cloud-sensitive — this is why Sentinel-1
SAR is the primary all-weather source and S2 is the secondary optical layer,
per docs/decisions/ml-layering.md Layer A observation gating).
"""

from __future__ import annotations

from datetime import date

from agritwin_etl.config import Settings


class Sentinel2Client:
    """Fetches Sentinel-2 L2A scenes (or derived indices) for a zone/date
    range via the Copernicus Data Space Ecosystem.

    Requires `Settings.sentinel_hub_client_id` and
    `Settings.sentinel_hub_client_secret` (OAuth2 client credentials flow).
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch_scenes(
        self, zone_geometry_wkt: str, start_date: date, end_date: date, max_cloud_pct: float = 20.0
    ) -> None:
        """Fetch L2A scenes intersecting `zone_geometry_wkt` in
        [`start_date`, `end_date`] with cloud cover below `max_cloud_pct`.

        Returns (once implemented): scene references with Red/NIR bands (for
        NDVI) and the L2A scene classification layer, for cloud/gap handling
        in packages/etl assets.
        """
        raise NotImplementedError(
            "Sentinel2Client.fetch_scenes: pending Copernicus Data Space "
            "OAuth credentials (Settings.sentinel_hub_client_id/secret)."
        )

"""Sentinel-1 RTC (Radiometrically Terrain Corrected) gamma0 client.

Per docs/decisions/data-access-layer.md: S1 GRD is NOT processed from scratch
(orbit correction, thermal noise removal, calibration, terrain flattening,
speckle filtering, geocoding — the full chain is not our responsibility).
This client fetches pre-built RTC gamma0 products only.

Terrain flattening and a layover/shadow mask are non-negotiable per that
record — the Aegean/Mediterranean pilot terrain (Ege region, per project
decision) is uneven enough that an unflattened backscatter signal loses the
moisture signal in slope shadow. Verify any provider's RTC product includes
both before wiring this client for real.
"""

from __future__ import annotations

from datetime import date

from agritwin_etl.config import Settings


class Sentinel1RTCClient:
    """Fetches pre-built Sentinel-1 RTC gamma0 scenes for a zone/date range.

    No credentials required by this stub's design point (RTC catalogs such as
    Microsoft Planetary Computer's Sentinel-1-RTC collection are public STAC),
    but a provider may require an API key — re-check when a concrete provider
    is chosen and add the field to `Settings` if so.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch_scenes(
        self, zone_geometry_wkt: str, start_date: date, end_date: date
    ) -> None:
        """Fetch RTC gamma0 scenes intersecting `zone_geometry_wkt` between
        `start_date` and `end_date` (inclusive).

        Returns (once implemented): a list of scene references (STAC items or
        equivalent) with VV/VH gamma0 bands, terrain-flattened, with an
        accompanying layover/shadow mask.
        """
        raise NotImplementedError(
            "Sentinel1RTCClient.fetch_scenes: pending provider selection and "
            "credentials. See docs/decisions/data-access-layer.md."
        )

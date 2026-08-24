"""SMAP (Soil Moisture Active Passive) client — NASA Earthdata.

Primary soil moisture data source per project decision (paired with ISMN as an
independent cross-validation pipeline — see ismn.py). 9 km resolution, daily.
Used as assimilation input to the twin (packages/twin), not a replacement for
the twin's own theta(z,t) estimate — see docs/modules.md#digital-twin.
"""

from __future__ import annotations

from datetime import date

from agritwin_etl.config import Settings


class SMAPClient:
    """Fetches SMAP soil moisture retrievals for a zone/date range via NASA
    Earthdata.

    Requires `Settings.nasa_earthdata_username` / `Settings.nasa_earthdata_password`.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch_retrievals(
        self, zone_geometry_wkt: str, start_date: date, end_date: date
    ) -> None:
        """Fetch SMAP L3/L4 soil moisture retrievals intersecting
        `zone_geometry_wkt` between `start_date` and `end_date`.

        Returns (once implemented): gridded volumetric moisture (m3/m3, see
        agritwin_core.units.VolumetricMoisture) with retrieval quality flags.
        """
        raise NotImplementedError(
            "SMAPClient.fetch_retrievals: pending NASA Earthdata credentials "
            "(Settings.nasa_earthdata_username/password)."
        )

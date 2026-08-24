"""ISMN (International Soil Moisture Network) client — cross-validation source.

Per project decision: SMAP is the primary soil moisture source; ISMN in-situ
station data runs as an independent second pipeline used to validate SMAP
retrievals against ground truth, not as a primary assimilation input. Station
coverage is sparse and point-based — do not use this as a gridded source.
"""

from __future__ import annotations

from datetime import date

from agritwin_etl.config import Settings


class ISMNClient:
    """Fetches ISMN in-situ soil moisture station data for cross-validating
    SMAP retrievals within a zone/date range.

    Requires `Settings.ismn_username` / `Settings.ismn_password`.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch_station_data(
        self, zone_geometry_wkt: str, start_date: date, end_date: date, max_distance_km: float = 25.0
    ) -> None:
        """Fetch ISMN station observations within `max_distance_km` of
        `zone_geometry_wkt`, between `start_date` and `end_date`.

        Returns (once implemented): point time series of volumetric moisture
        (m3/m3) at station depth, for the SMAP cross-validation pipeline.
        May return zero stations for a given zone — sparse network coverage is
        expected, not an error condition.
        """
        raise NotImplementedError(
            "ISMNClient.fetch_station_data: pending ISMN credentials "
            "(Settings.ismn_username/password)."
        )

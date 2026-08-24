"""SoilGrids client — static, one-off download.

Per docs/decisions/data-access-layer.md: SoilGrids is a static one-off
download, not a recurring Dagster asset. Provides texture class (used in
PARCEL_ADAPTATION.cohort_key — "texture class x climate zone x irrigation
method", see docs/schemas.md) and other static soil properties that do not
change on a zone-day cadence.

Because this is a one-time fetch, it should NOT be wired as a
DailyPartitionsDefinition asset like the other sources in
agritwin_etl.assets — see feature_store_zone_day.py, which treats SoilGrids
output as a slowly-changing dimension joined in, not a partitioned input.
"""

from __future__ import annotations

from agritwin_etl.config import Settings


class SoilGridsClient:
    """Fetches static soil property rasters (texture, bulk density, etc.) for
    the pilot region. No credentials required — SoilGrids is a public REST/WCS
    service.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch_static_properties(self, region_geometry_wkt: str) -> None:
        """One-time fetch of SoilGrids properties for `region_geometry_wkt`
        (expected to cover the full pilot region, not per-zone).

        Returns (once implemented): static soil texture/property rasters to
        be joined into PARCEL_ADAPTATION.cohort_key derivation.
        """
        raise NotImplementedError(
            "SoilGridsClient.fetch_static_properties: not yet implemented. "
            "Public API, no credentials needed — implementation pending."
        )

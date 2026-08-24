"""Open-Meteo client — OPERATIONAL weather forcing line.

Per docs/decisions/weather-forcing-split.md: this is the low-latency
operational line used for daily inference and 24-48h recipe generation.
Open-Meteo is named explicitly in that record as the aggregator for "the
first phase." Provides the full FAO-56 Penman-Monteith input set: temperature,
humidity, wind speed, solar radiation.

Contrast with weather_era5.py (archive line) — the two must never be mixed
in the operational path. See that module's docstring for the prohibition.
"""

from __future__ import annotations

from datetime import date

from agritwin_etl.config import Settings


class OpenMeteoClient:
    """Fetches near-real-time and short-range forecast weather for a zone.

    No API key required for Open-Meteo's free tier —
    `Settings.open_meteo_api_key` may remain unset.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch_forecast(self, latitude: float, longitude: float, days_ahead: int = 2) -> None:
        """Fetch hourly forecast (temperature, humidity, wind, solar
        radiation) for the next `days_ahead` days at (`latitude`,
        `longitude`) — feeds the 24-48h recipe generation window.

        Returns (once implemented): hourly meteorological series for
        FAO-56 Penman-Monteith ET0 computation (see
        docs/fao56-calculations.md).
        """
        raise NotImplementedError(
            "OpenMeteoClient.fetch_forecast: not yet implemented."
        )

    def fetch_recent_observed(
        self, latitude: float, longitude: float, start_date: date, end_date: date
    ) -> None:
        """Fetch recent observed (not forecast) hourly weather for
        (`latitude`, `longitude`) between `start_date` and `end_date` — used
        to backfill the operational zone-day table for days already elapsed.
        """
        raise NotImplementedError(
            "OpenMeteoClient.fetch_recent_observed: not yet implemented."
        )

from agritwin_etl.assets.feature_store_zone_day import feature_store_zone_day
from agritwin_etl.assets.ismn_zone_day import ismn_zone_day
from agritwin_etl.assets.landsat_zone_day import landsat_zone_day
from agritwin_etl.assets.sentinel1_zone_day import sentinel1_zone_day
from agritwin_etl.assets.sentinel2_zone_day import sentinel2_zone_day
from agritwin_etl.assets.smap_zone_day import smap_zone_day
from agritwin_etl.assets.weather_archive_zone_day import weather_archive_zone_day
from agritwin_etl.assets.weather_operational_zone_day import weather_operational_zone_day

all_assets = [
    sentinel1_zone_day,
    sentinel2_zone_day,
    landsat_zone_day,
    smap_zone_day,
    ismn_zone_day,
    weather_operational_zone_day,
    weather_archive_zone_day,
    feature_store_zone_day,
]

__all__ = ["all_assets"]

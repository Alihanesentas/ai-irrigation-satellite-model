from datetime import datetime, timedelta, timezone

import pytest

from agritwin_core.units import (
    AreaM2,
    DepthMM,
    VolumetricMoisture,
    VolumeL,
    depth_to_volume,
    require_utc,
    volume_to_zone_average_depth,
)


def test_volumetric_moisture_rejects_out_of_range():
    with pytest.raises(ValueError):
        VolumetricMoisture(1.5)
    with pytest.raises(ValueError):
        VolumetricMoisture(-0.01)


def test_area_m2_rejects_non_positive():
    with pytest.raises(ValueError):
        AreaM2(0)
    with pytest.raises(ValueError):
        AreaM2(-5)


def test_volume_to_zone_average_depth_matches_schemas_definition():
    # docs/schemas.md: "measured_depth_mm ... volume_l / area_m2"
    depth = volume_to_zone_average_depth(VolumeL(10_000), AreaM2(1_000))
    assert depth == DepthMM(10.0)


def test_depth_to_volume_is_the_inverse_of_volume_to_zone_average_depth():
    area = AreaM2(1_000)
    volume = depth_to_volume(DepthMM(10.0), area)
    assert volume == VolumeL(10_000)
    assert volume_to_zone_average_depth(volume, area) == DepthMM(10.0)


def test_depth_mm_arithmetic_stays_within_unit():
    assert DepthMM(3.0) + DepthMM(2.0) == DepthMM(5.0)
    assert DepthMM(5.0) - DepthMM(2.0) == DepthMM(3.0)
    assert DepthMM(2.0) * 3 == DepthMM(6.0)


def test_require_utc_rejects_naive_datetime():
    with pytest.raises(ValueError):
        require_utc(datetime(2026, 1, 1))


def test_require_utc_rejects_non_utc_offset():
    tz = timezone(timedelta(hours=3))
    with pytest.raises(ValueError):
        require_utc(datetime(2026, 1, 1, tzinfo=tz))


def test_require_utc_accepts_utc():
    dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert require_utc(dt) is dt

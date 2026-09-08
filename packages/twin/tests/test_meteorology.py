import math

import pytest

from agritwin_twin import meteorology as met


def test_sunset_hour_angle_is_close_to_half_pi_at_equator_equinox():
    # Equator, day 80 (~March equinox): declination ~0, day length ~12h,
    # so the sunset hour angle should sit close to pi/2 (90 degrees).
    delta = met.solar_declination(80)
    omega_s = met.sunset_hour_angle(0.0, delta)
    assert omega_s == pytest.approx(math.pi / 2, abs=0.05)


def test_extraterrestrial_radiation_is_positive_and_peaks_near_summer_solstice_manisa():
    lat = math.radians(38.614)  # Manisa
    ra_summer = met.extraterrestrial_radiation(172, lat)  # ~June 21
    ra_winter = met.extraterrestrial_radiation(355, lat)  # ~Dec 21
    assert ra_summer > 0
    assert ra_winter > 0
    assert ra_summer > ra_winter  # Northern hemisphere: summer Ra > winter Ra


def test_saturation_vapor_pressure_increases_with_temperature():
    assert met.e_sat(30.0) > met.e_sat(10.0) > met.e_sat(0.0) > 0


def test_actual_vapor_pressure_from_dewpoint_equals_e_sat_at_dewpoint():
    assert met.actual_vapor_pressure_from_dewpoint(15.0) == met.e_sat(15.0)


def test_actual_vapor_pressure_dispatch_prefers_dewpoint_over_rh():
    ea_dewpoint = met.actual_vapor_pressure(
        tmax_c=25, tmin_c=15, tdew_c=12.0, rh_max_pct=90, rh_min_pct=30, rh_mean_pct=None
    )
    assert ea_dewpoint == met.actual_vapor_pressure_from_dewpoint(12.0)


def test_actual_vapor_pressure_requires_at_least_one_humidity_input():
    with pytest.raises(ValueError):
        met.actual_vapor_pressure(
            tmax_c=25, tmin_c=15, tdew_c=None, rh_max_pct=None, rh_min_pct=None, rh_mean_pct=None
        )


def test_wind_speed_2m_reduces_a_10m_measurement():
    # Wind is slower near the ground; a 10 m reading should scale down.
    u10 = 4.0
    u2 = met.wind_speed_2m(u10, measurement_height_m=10.0)
    assert 0 < u2 < u10


def test_wind_speed_2m_is_identity_at_2m():
    assert met.wind_speed_2m(3.5, measurement_height_m=2.0) == 3.5


def test_reference_et0_is_positive_and_plausible_for_a_hot_dry_manisa_summer_day():
    result = met.reference_et0(
        day_of_year=200,
        latitude_rad=math.radians(38.614),
        elevation_m=71,
        tmax_c=35.0,
        tmin_c=20.0,
        rs_mj_m2_day=27.0,
        wind_speed_ms=2.5,
        wind_height_m=10.0,
        rh_max_pct=45.0,
        rh_min_pct=15.0,
    )
    # A hot, dry, sunny Aegean summer day: FAO-56-typical ET0 sits roughly
    # in the 5-10 mm/day band for this kind of forcing.
    assert 3.0 < result.et0.value < 12.0
    assert result.rn > 0


def test_reference_et0_rises_with_temperature_all_else_equal():
    kwargs = dict(
        day_of_year=200,
        latitude_rad=math.radians(38.614),
        elevation_m=71,
        rs_mj_m2_day=25.0,
        wind_speed_ms=2.0,
        wind_height_m=10.0,
        rh_max_pct=50.0,
        rh_min_pct=20.0,
    )
    cool = met.reference_et0(tmax_c=25.0, tmin_c=15.0, **kwargs)
    hot = met.reference_et0(tmax_c=38.0, tmin_c=24.0, **kwargs)
    assert hot.et0.value > cool.et0.value

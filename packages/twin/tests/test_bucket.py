import math
from datetime import datetime, timezone

from agritwin_core.units import DepthMM
from agritwin_twin.crops import GRAPE_MANISA, OLIVE_MANISA
from agritwin_twin.interface import DailyForcing
from agritwin_twin.models.bucket import BucketConfig, BucketModel
from agritwin_twin.soils import CLAY_LOAM_MANISA

MANISA_LAT = math.radians(38.614)
MANISA_ELEV = 71.0


def _hot_dry_summer_day(day: int) -> DailyForcing:
    # August 1 + day: comfortably inside both crops' mid-season stage
    # (olive mid starts ~day 211/doy, grape mid starts ~doy 175), so Kcb is
    # at its full mid-season value rather than still ramping through `dev`.
    return DailyForcing(
        date_utc=datetime(2026, 8, day, tzinfo=timezone.utc),
        tmax_c=36.0,
        tmin_c=22.0,
        rs_mj_m2_day=28.0,
        wind_speed_ms=2.0,
        wind_height_m=10.0,
        precip_mm=0.0,
        rh_max_pct=45.0,
        rh_min_pct=15.0,
    )


def _rainy_day() -> DailyForcing:
    return DailyForcing(
        date_utc=datetime(2026, 1, 15, tzinfo=timezone.utc),
        tmax_c=12.0,
        tmin_c=6.0,
        rs_mj_m2_day=6.0,
        wind_speed_ms=3.0,
        wind_height_m=10.0,
        precip_mm=40.0,
        rh_max_pct=90.0,
        rh_min_pct=60.0,
    )


def _make_bucket(crop, percolation_mode="fao56_instant", initial_dr_mm=None) -> BucketModel:
    config = BucketConfig(
        crop=crop,
        soil=CLAY_LOAM_MANISA,
        latitude_rad=MANISA_LAT,
        elevation_m=MANISA_ELEV,
        percolation_mode=percolation_mode,
    )
    return BucketModel(config, initial_dr_mm=initial_dr_mm)


def test_repeated_dry_hot_days_increase_depletion_and_trigger_stress():
    crop = GRAPE_MANISA
    taw = 1000 * (CLAY_LOAM_MANISA.theta_fc - CLAY_LOAM_MANISA.theta_wp) * crop.root_depth_max_m
    raw = crop.depletion_fraction_p * taw
    # Start already close to RAW so a couple of weeks of unmitigated
    # mid-season ETc is guaranteed to push depletion past it, regardless of
    # the exact daily ETc rate this configuration produces.
    bucket = _make_bucket(crop, initial_dr_mm=raw * 0.85)
    zero_depth = DepthMM(0.0)
    states = []
    for day in range(1, 15):
        state = bucket.step(_hot_dry_summer_day(day), zero_depth)
        states.append(state)

    assert states[-1].dr_mm.value > states[0].dr_mm.value
    # Depletion should be monotonically non-decreasing with no water input.
    for prev, curr in zip(states, states[1:]):
        assert curr.dr_mm.value >= prev.dr_mm.value - 1e-9
    # Enough consecutive dry days should eventually depress Ks below 1.
    assert any(s.ks_stress < 1.0 for s in states)


def test_theta_never_leaves_physical_bounds_under_dry_stress():
    bucket = _make_bucket(GRAPE_MANISA, initial_dr_mm=0.0)
    zero_depth = DepthMM(0.0)
    for day in range(1, 29):
        state = bucket.step(_hot_dry_summer_day(day), zero_depth)
        assert 0.0 <= state.theta.value <= 1.0


def test_fao56_instant_percolation_clamps_depletion_to_zero_after_heavy_rain():
    crop = OLIVE_MANISA
    # Start close to field capacity (small depletion) so a 40mm rain event
    # exceeds what the bucket can hold and must overflow to DP.
    bucket = _make_bucket(crop, percolation_mode="fao56_instant", initial_dr_mm=15.0)
    state = bucket.step(_rainy_day(), DepthMM(0.0))

    # A 40mm rain event on a soil already half-depleted should saturate the
    # bucket: Dr clamps to 0 immediately (instant-drain assumption).
    assert state.dr_mm.value == 0.0
    assert bucket.last_diagnostics is not None
    assert bucket.last_diagnostics.deep_percolation_mm > 0


def test_van_genuchten_percolation_drains_more_gradually_than_instant():
    crop = OLIVE_MANISA
    taw = 1000 * (CLAY_LOAM_MANISA.theta_fc - CLAY_LOAM_MANISA.theta_wp) * crop.root_depth_max_m
    initial_dr = taw * 0.1  # already near field capacity

    instant = _make_bucket(crop, percolation_mode="fao56_instant", initial_dr_mm=initial_dr)
    vg = _make_bucket(crop, percolation_mode="van_genuchten", initial_dr_mm=initial_dr)

    forcing = _rainy_day()
    state_instant = instant.step(forcing, DepthMM(0.0))
    state_vg = vg.step(forcing, DepthMM(0.0))

    # Near field capacity, the instant-drain model dumps everything above
    # zero depletion in one step; the van Genuchten model's conductivity at
    # a near-field-capacity moisture is far below Ks, so it should drain
    # less of the same excess water in the same single day, leaving a
    # nonzero (or at least not-lower) depletion relative to the instant
    # model. This is the qualitative behaviour difference the two
    # percolation modes exist to demonstrate.
    assert state_vg.dr_mm.value >= state_instant.dr_mm.value


def test_irrigation_reduces_depletion():
    bucket = _make_bucket(GRAPE_MANISA, initial_dr_mm=20.0)
    forcing = _hot_dry_summer_day(1)
    dr_before = bucket.state().dr_mm.value
    state = bucket.step(forcing, DepthMM(15.0))
    # 15mm irrigation should offset most/all of a hot day's ETc, netting a
    # lower (or at least not much higher) depletion than doing nothing.
    baseline = _make_bucket(GRAPE_MANISA, initial_dr_mm=20.0)
    state_no_irrigation = baseline.step(forcing, DepthMM(0.0))
    assert state.dr_mm.value < state_no_irrigation.dr_mm.value


def test_extrapolate_freezes_state_and_degrades_confidence_after_threshold():
    bucket = _make_bucket(OLIVE_MANISA, initial_dr_mm=10.0)
    bucket.step(_hot_dry_summer_day(1), DepthMM(0.0))
    frozen_theta = bucket.state().theta

    last_state = None
    for day in range(10):
        last_state = bucket.extrapolate(datetime(2026, 7, 2 + day, tzinfo=timezone.utc))
        assert last_state.theta == frozen_theta  # never guesses a new value

    assert last_state.confidence == "low"

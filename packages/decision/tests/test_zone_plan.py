from datetime import datetime, timezone

from agritwin_core.schema import IrrigationMethod, Zone
from agritwin_core.units import DepthMM, VolumetricMoisture
from agritwin_twin.interface import SoilState

from agritwin_decision.policy import IrrigationPolicy
from agritwin_decision.zone_plan import plan_zone_need


def _zone(area_m2: float = 1000.0, flow_l_min: float = 50.0) -> Zone:
    return Zone(
        zone_id="z1",
        parcel_id="prc_1",
        area_m2=area_m2,
        irrigation_method=IrrigationMethod.SURFACE_DRIP,
        nominal_flow_l_min=flow_l_min,
        meter_k_factor_l_per_pulse=1.0,
    )


def _soil_state(dr_mm: float, raw_mm: float = 100.0, taw_mm: float = 200.0, confidence: str = "normal") -> SoilState:
    return SoilState(
        valid_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        theta=VolumetricMoisture(0.25),
        theta_std=None,
        dr_mm=DepthMM(dr_mm),
        ks_stress=1.0,
        raw_mm=DepthMM(raw_mm),
        taw_mm=DepthMM(taw_mm),
        confidence=confidence,
    )


def test_no_need_when_depletion_below_raw():
    need = plan_zone_need(_soil_state(dr_mm=50.0, raw_mm=100.0), _zone())
    assert need is None


def test_need_triggers_at_raw_with_default_policy():
    need = plan_zone_need(_soil_state(dr_mm=100.0, raw_mm=100.0), _zone())
    assert need is not None
    assert need.target_depth_mm.value == 100.0  # full refill by default


def test_duration_matches_volume_over_flow_rate():
    # 100mm over 1000 m2 = 100,000 L; at 50 L/min that's 2000 min = 120,000s
    need = plan_zone_need(
        _soil_state(dr_mm=100.0, raw_mm=100.0), _zone(area_m2=1000.0, flow_l_min=50.0)
    )
    assert need is not None
    assert need.duration_s == 120_000


def test_low_confidence_dampens_target_depth():
    policy = IrrigationPolicy()
    normal = plan_zone_need(_soil_state(dr_mm=100.0, raw_mm=100.0, confidence="normal"), _zone(), policy)
    low = plan_zone_need(_soil_state(dr_mm=100.0, raw_mm=100.0, confidence="low"), _zone(), policy)
    assert normal is not None and low is not None
    assert low.target_depth_mm.value < normal.target_depth_mm.value
    assert low.target_depth_mm.value == 100.0 * policy.low_confidence_refill_fraction


def test_urgency_scales_with_depletion_past_trigger():
    just_over = plan_zone_need(_soil_state(dr_mm=101.0, raw_mm=100.0), _zone())
    way_over = plan_zone_need(_soil_state(dr_mm=180.0, raw_mm=100.0), _zone())
    assert just_over is not None and way_over is not None
    assert way_over.urgency > just_over.urgency


def test_custom_policy_partial_refill():
    policy = IrrigationPolicy(target_refill_fraction=0.5)
    need = plan_zone_need(_soil_state(dr_mm=100.0, raw_mm=100.0), _zone(), policy)
    assert need is not None
    assert need.target_depth_mm.value == 50.0

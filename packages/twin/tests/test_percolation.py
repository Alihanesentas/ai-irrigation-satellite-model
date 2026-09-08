from agritwin_twin.percolation import (
    effective_saturation,
    matric_potential_m,
    unsaturated_hydraulic_conductivity_m_per_day,
    van_genuchten_drainage_mm_per_day,
)
from agritwin_twin.soils import CLAY_LOAM_MANISA


def test_effective_saturation_is_zero_at_residual_and_one_at_saturation():
    assert effective_saturation(CLAY_LOAM_MANISA.theta_r, CLAY_LOAM_MANISA) == 0.0
    assert effective_saturation(CLAY_LOAM_MANISA.theta_s, CLAY_LOAM_MANISA) == 1.0


def test_effective_saturation_clamps_outside_physical_range():
    assert effective_saturation(CLAY_LOAM_MANISA.theta_r - 0.05, CLAY_LOAM_MANISA) == 0.0
    assert effective_saturation(CLAY_LOAM_MANISA.theta_s + 0.05, CLAY_LOAM_MANISA) == 1.0


def test_matric_potential_is_zero_at_saturation_and_negative_below():
    assert matric_potential_m(CLAY_LOAM_MANISA.theta_s, CLAY_LOAM_MANISA) == 0.0
    assert matric_potential_m(CLAY_LOAM_MANISA.theta_fc, CLAY_LOAM_MANISA) < 0.0


def test_hydraulic_conductivity_is_zero_at_residual_and_ks_at_saturation():
    k_dry = unsaturated_hydraulic_conductivity_m_per_day(CLAY_LOAM_MANISA.theta_r, CLAY_LOAM_MANISA)
    k_sat = unsaturated_hydraulic_conductivity_m_per_day(CLAY_LOAM_MANISA.theta_s, CLAY_LOAM_MANISA)
    assert k_dry == 0.0
    assert k_sat == CLAY_LOAM_MANISA.ks_vg_m_per_day


def test_hydraulic_conductivity_rises_steeply_near_saturation():
    # docs/fao56-calculations.md section 11.2: "K(theta) rises extremely
    # steeply" near theta_s. Confirm the qualitative shape: conductivity at
    # field capacity is much smaller than at saturation.
    k_fc = unsaturated_hydraulic_conductivity_m_per_day(CLAY_LOAM_MANISA.theta_fc, CLAY_LOAM_MANISA)
    k_sat = unsaturated_hydraulic_conductivity_m_per_day(CLAY_LOAM_MANISA.theta_s, CLAY_LOAM_MANISA)
    assert 0 < k_fc < 0.3 * k_sat


def test_van_genuchten_drainage_is_a_thousand_times_the_conductivity_in_meters():
    k = unsaturated_hydraulic_conductivity_m_per_day(CLAY_LOAM_MANISA.theta_fc, CLAY_LOAM_MANISA)
    drainage = van_genuchten_drainage_mm_per_day(CLAY_LOAM_MANISA.theta_fc, CLAY_LOAM_MANISA)
    assert drainage == k * 1000.0

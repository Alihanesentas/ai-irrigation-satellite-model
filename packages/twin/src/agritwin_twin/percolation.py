"""Van Genuchten-Mualem unsaturated hydraulic conductivity, K(theta) — the
"flow coefficient" governing how fast water moves down out of the root zone
under gravity, used here as a **physically-motivated alternative** to the
standard FAO-56 bucket's instant-drain deep percolation term.

This is deliberately NOT the full 1D Richards PDE (that is Phase 3's PINN,
`docs/fao56-calculations.md` section 11.2, which solves `theta(z,t)` as a
continuous profile). What this module provides is the same section's
constitutive relations (`psi_vg`, `K_vg`) applied as a **single-point,
free-drainage approximation** at the bottom of the root-zone bucket:

    q_drainage = -K(theta) * (d(psi)/dz + 1)

Under the section 11.2 bottom-boundary "free drainage" assumption
(`d(psi)/dz = 0`, unit hydraulic gradient — "a standard simplification when
no water table data exists", which matches this project's zero-sensor
premise exactly), this collapses to `q_drainage = K(theta)`: gravity alone
drives the flux, no explicit pressure gradient needed. `K(theta)` rises
steeply near saturation and drops off orders of magnitude as the soil dries
(`docs/fao56-calculations.md` section 11.2, "why this is stiff") — which is
exactly the "moisture reaching the roots is not the same as surface
moisture" distinction: a bucket sitting well above field capacity drains
fast under this model, while the standard FAO-56 treatment (see
`models/bucket.py::deep_percolation_fao56`) drains the same excess
*instantly*, in one timestep, regardless of how saturated the soil actually
is.

The benchmark notebook (`experiments/notebooks/`) runs both percolation
models side by side for the same crop/weather series specifically so this
difference is visible rather than assumed.
"""

from __future__ import annotations

from agritwin_twin.soils import SoilParameters


def effective_saturation(theta: float, soil: SoilParameters) -> float:
    """Se(theta), dimensionless, section 11.2. Clamped to [0, 1] — `theta`
    can sit fractionally outside [theta_r, theta_s] due to bucket-model
    numerical slack at the boundaries; the physical quantity cannot."""
    se = (theta - soil.theta_r) / (soil.theta_s - soil.theta_r)
    return max(0.0, min(1.0, se))


def matric_potential_m(theta: float, soil: SoilParameters) -> float:
    """psi_vg(Se), m (negative — suction), section 11.2's water retention
    curve. Returns 0.0 at full saturation (Se=1) rather than dividing by
    zero in `Se^(-1/m)`."""
    se = effective_saturation(theta, soil)
    if se >= 1.0:
        return 0.0
    m = soil.m_vg()
    return -(1 / soil.alpha_vg_per_m) * (se ** (-1 / m) - 1) ** (1 / soil.n_vg)


def unsaturated_hydraulic_conductivity_m_per_day(theta: float, soil: SoilParameters) -> float:
    """K_vg(Se), m/day — section 11.2's Mualem-form conductivity function,
    the "flow coefficient" this module exists to compute. Zero at Se=0 by
    construction (bone-dry soil transmits nothing), rising to `ks_vg_m_per_day`
    at full saturation.
    """
    se = effective_saturation(theta, soil)
    if se <= 0.0:
        return 0.0
    m = soil.m_vg()
    inner = 1 - (1 - se ** (1 / m)) ** m
    return soil.ks_vg_m_per_day * (se**soil.l_mualem) * inner**2


def van_genuchten_drainage_mm_per_day(theta: float, soil: SoilParameters) -> float:
    """Deep percolation flux out of the root zone, mm/day, under the
    free-drainage (unit hydraulic gradient) bottom-boundary assumption —
    `q_drainage = K(theta)`, converted from m/day to mm/day. This is the
    quantity `models/bucket.py`'s van-Genuchten-informed percolation mode
    substitutes for FAO-56's instant-drain `DP` term (section 9.2).
    """
    return unsaturated_hydraulic_conductivity_m_per_day(theta, soil) * 1000.0


__all__ = [
    "effective_saturation",
    "matric_potential_m",
    "unsaturated_hydraulic_conductivity_m_per_day",
    "van_genuchten_drainage_mm_per_day",
]

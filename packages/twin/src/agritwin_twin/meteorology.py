"""FAO-56 Penman-Monteith reference evapotranspiration (ET0) and its inputs.

Direct implementation of `docs/fao56-calculations.md` sections 1-7. Every
function below corresponds to one named formula in that document and reuses
its code identifiers (`Ra`, `Rn`, `es`, `ea`, `Delta_vp`, `gamma_psychro`,
`u2`, `ET0`, ...) so the reference doc and this module can be read side by
side. Primary source: Allen, Pereira, Raes, Smith (1998), FAO Irrigation and
Drainage Paper 56.

All angle inputs/outputs are radians unless a name ends in `_deg`. All
temperatures are °C unless a name ends in `_k` (Kelvin, only used inside the
Stefan-Boltzmann term, per `docs/fao56-calculations.md` section 10's unit
table).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from agritwin_core.constants import (
    KELVIN_OFFSET_C,
    REFERENCE_ALBEDO,
    SOLAR_CONSTANT_MJ_M2_MIN,
    STANDARD_ATMOSPHERIC_PRESSURE_KPA,
    STEFAN_BOLTZMANN_MJ_K4_M2_DAY,
    WIND_MEASUREMENT_HEIGHT_STANDARD_M,
)
from agritwin_core.units import DepthMM


# --- Section 1: extraterrestrial radiation ---------------------------------


def solar_declination(day_of_year: int) -> float:
    """delta_solar, radians. `docs/fao56-calculations.md` section 1."""
    return 0.409 * math.sin(2 * math.pi / 365 * day_of_year - 1.39)


def inverse_relative_distance(day_of_year: int) -> float:
    """dr, dimensionless. Section 1."""
    return 1 + 0.033 * math.cos(2 * math.pi / 365 * day_of_year)


def sunset_hour_angle(latitude_rad: float, delta_solar: float) -> float:
    """omega_s, radians. Section 1.

    Clamped: at latitudes/seasons where the sun never sets or never rises,
    `tan(phi)*tan(delta)` can fall outside [-1, 1] by a hair from float
    error even when physically valid — clamp rather than let `acos` raise.
    """
    x = -math.tan(latitude_rad) * math.tan(delta_solar)
    return math.acos(max(-1.0, min(1.0, x)))


def extraterrestrial_radiation(
    day_of_year: int, latitude_rad: float
) -> float:
    """Ra, MJ m-2 day-1. Section 1."""
    delta = solar_declination(day_of_year)
    dr = inverse_relative_distance(day_of_year)
    omega_s = sunset_hour_angle(latitude_rad, delta)
    return (
        (24 * 60 / math.pi)
        * SOLAR_CONSTANT_MJ_M2_MIN
        * dr
        * (
            omega_s * math.sin(latitude_rad) * math.sin(delta)
            + math.cos(latitude_rad) * math.cos(delta) * math.sin(omega_s)
        )
    )


# --- Section 2: net radiation -----------------------------------------------


def clear_sky_radiation(ra: float, elevation_m: float) -> float:
    """Rso, MJ m-2 day-1. Section 2.2."""
    return (0.75 + 2e-5 * elevation_m) * ra


def net_shortwave_radiation(rs: float, albedo: float = REFERENCE_ALBEDO) -> float:
    """Rns, MJ m-2 day-1. Section 2.1."""
    return (1 - albedo) * rs


def net_longwave_radiation(
    tmax_c: float, tmin_c: float, ea_kpa: float, rs: float, rso: float
) -> float:
    """Rnl, MJ m-2 day-1. Section 2.2. `Rs/Rso` capped at 1.0 (documented
    cloudiness-ratio bound; without the cap a slightly-overcast-corrected Rs
    can exceed Rso by float noise near clear-sky conditions)."""
    tmax_k = tmax_c + KELVIN_OFFSET_C
    tmin_k = tmin_c + KELVIN_OFFSET_C
    cloudiness = min(rs / rso, 1.0) if rso > 0 else 1.0
    return (
        STEFAN_BOLTZMANN_MJ_K4_M2_DAY
        * ((tmax_k**4 + tmin_k**4) / 2)
        * (0.34 - 0.14 * math.sqrt(max(ea_kpa, 0.0)))
        * (1.35 * cloudiness - 0.35)
    )


def net_radiation(rns: float, rnl: float) -> float:
    """Rn, MJ m-2 day-1. Section 2.3."""
    return rns - rnl


# --- Section 4: psychrometric constant --------------------------------------


def atmospheric_pressure(elevation_m: float) -> float:
    """P_atm, kPa. Section 4."""
    return STANDARD_ATMOSPHERIC_PRESSURE_KPA * ((293 - 0.0065 * elevation_m) / 293) ** 5.26


def psychrometric_constant(elevation_m: float) -> float:
    """gamma_psychro, kPa degC-1. Section 4 (approximated form, `0.665e-3 * P`,
    which folds cp/epsilon/lambda into one constant — same simplification
    the reference doc states FAO-56 accepts)."""
    return 0.665e-3 * atmospheric_pressure(elevation_m)


# --- Section 5: vapor pressure terms ----------------------------------------


def e_sat(temp_c: float) -> float:
    """e_deg(T), kPa — saturation vapor pressure at a single temperature.
    Section 5.1, the `e_deg` helper."""
    return 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))


def mean_saturation_vapor_pressure(tmax_c: float, tmin_c: float) -> float:
    """es, kPa. Section 5.1 — mean of e_deg(Tmax) and e_deg(Tmin), not
    e_deg(Tmean): using Tmean underestimates es because e_deg(T) is convex."""
    return (e_sat(tmax_c) + e_sat(tmin_c)) / 2


def actual_vapor_pressure_from_rh_minmax(
    tmax_c: float, tmin_c: float, rh_max_pct: float, rh_min_pct: float
) -> float:
    """ea, kPa, from RHmax/RHmin. Section 5.2, preferred RH-based form."""
    return (e_sat(tmin_c) * rh_max_pct / 100 + e_sat(tmax_c) * rh_min_pct / 100) / 2


def actual_vapor_pressure_from_rh_mean(
    tmax_c: float, tmin_c: float, rh_mean_pct: float
) -> float:
    """ea, kPa, from RHmean only. Section 5.2 — the lower-quality fallback;
    callers should flag `data_quality` accordingly per the `schemas.md`
    convention this doc calls out."""
    return rh_mean_pct / 100 * (e_sat(tmax_c) + e_sat(tmin_c)) / 2


def actual_vapor_pressure_from_dewpoint(tdew_c: float) -> float:
    """ea, kPa, from dewpoint. Section 5.2 — "the more numerically stable
    path, preferred when available" (both ERA5-Land and Open-Meteo supply
    this)."""
    return e_sat(tdew_c)


def slope_saturation_vapor_pressure_curve(tmax_c: float, tmin_c: float) -> float:
    """Delta_vp, kPa degC-1, evaluated at mean daily temperature. Section 5.3."""
    t_mean = (tmax_c + tmin_c) / 2
    return 4098 * e_sat(t_mean) / (t_mean + 237.3) ** 2


# --- Section 6: wind speed adjustment ---------------------------------------


def wind_speed_2m(
    wind_speed_ms: float, measurement_height_m: float = WIND_MEASUREMENT_HEIGHT_STANDARD_M
) -> float:
    """u2, m s-1. Section 6. Identity when already measured at 2 m."""
    if measurement_height_m == 2.0:
        return wind_speed_ms
    return wind_speed_ms * 4.87 / math.log(67.8 * measurement_height_m - 5.42)


# --- Section 7: ET0 ----------------------------------------------------------


def actual_vapor_pressure(
    *,
    tmax_c: float,
    tmin_c: float,
    tdew_c: float | None,
    rh_max_pct: float | None,
    rh_min_pct: float | None,
    rh_mean_pct: float | None,
) -> float:
    """Dispatches to the best available `ea` method per section 5.2's stated
    preference order: dewpoint > RHmax/RHmin > RHmean."""
    if tdew_c is not None:
        return actual_vapor_pressure_from_dewpoint(tdew_c)
    if rh_max_pct is not None and rh_min_pct is not None:
        return actual_vapor_pressure_from_rh_minmax(tmax_c, tmin_c, rh_max_pct, rh_min_pct)
    if rh_mean_pct is not None:
        return actual_vapor_pressure_from_rh_mean(tmax_c, tmin_c, rh_mean_pct)
    raise ValueError(
        "actual_vapor_pressure: need tdew_c, or (rh_max_pct and rh_min_pct), "
        "or rh_mean_pct — none were provided"
    )


@dataclass(frozen=True, slots=True)
class ET0Breakdown:
    """Every intermediate the reference ET0 calculation produces, kept
    alongside the final value so a benchmark notebook can plot/inspect the
    radiation vs. aerodynamic term split described in
    `docs/fao56-calculations.md` section 7 ("This dominates on calm, sunny
    days" / "This dominates on windy, dry days") rather than only seeing the
    summed result."""

    et0: DepthMM
    rn: float
    ra: float
    rso: float
    es: float
    ea: float
    delta_vp: float
    gamma_psychro: float
    u2: float
    radiation_term_mm: float
    aerodynamic_term_mm: float


def reference_et0(
    *,
    day_of_year: int,
    latitude_rad: float,
    elevation_m: float,
    tmax_c: float,
    tmin_c: float,
    rs_mj_m2_day: float,
    wind_speed_ms: float,
    wind_height_m: float = WIND_MEASUREMENT_HEIGHT_STANDARD_M,
    tdew_c: float | None = None,
    rh_max_pct: float | None = None,
    rh_min_pct: float | None = None,
    rh_mean_pct: float | None = None,
    soil_heat_flux_mj_m2_day: float = 0.0,
) -> ET0Breakdown:
    """Full FAO-56 Penman-Monteith ET0, section 7's formula, term for term.

    `soil_heat_flux_mj_m2_day` defaults to 0 — section 3: "G is negligible
    relative to Rn for daily calculations", the daily timestep this system
    always runs at (`docs/open-decisions.md`).
    """
    ra = extraterrestrial_radiation(day_of_year, latitude_rad)
    rso = clear_sky_radiation(ra, elevation_m)
    es = mean_saturation_vapor_pressure(tmax_c, tmin_c)
    ea = actual_vapor_pressure(
        tmax_c=tmax_c,
        tmin_c=tmin_c,
        tdew_c=tdew_c,
        rh_max_pct=rh_max_pct,
        rh_min_pct=rh_min_pct,
        rh_mean_pct=rh_mean_pct,
    )
    rns = net_shortwave_radiation(rs_mj_m2_day)
    rnl = net_longwave_radiation(tmax_c, tmin_c, ea, rs_mj_m2_day, rso)
    rn = net_radiation(rns, rnl)
    delta_vp = slope_saturation_vapor_pressure_curve(tmax_c, tmin_c)
    gamma = psychrometric_constant(elevation_m)
    u2 = wind_speed_2m(wind_speed_ms, wind_height_m)
    t_mean = (tmax_c + tmin_c) / 2

    radiation_term = 0.408 * delta_vp * (rn - soil_heat_flux_mj_m2_day)
    aerodynamic_term = gamma * (900 / (t_mean + 273)) * u2 * (es - ea)
    denominator = delta_vp + gamma * (1 + 0.34 * u2)

    et0_value = max(0.0, (radiation_term + aerodynamic_term) / denominator)

    return ET0Breakdown(
        et0=DepthMM(et0_value),
        rn=rn,
        ra=ra,
        rso=rso,
        es=es,
        ea=ea,
        delta_vp=delta_vp,
        gamma_psychro=gamma,
        u2=u2,
        radiation_term_mm=radiation_term / denominator,
        aerodynamic_term_mm=aerodynamic_term / denominator,
    )

"""Physical constants for FAO-56 Penman-Monteith ET0 and related calculations.

Full derivations, worked examples, and the complete equation chain (extraterrestrial
radiation -> clear-sky radiation -> net radiation -> ET0) live in
`docs/fao56-calculations.md`. This module holds only the numeric constants FAO
Irrigation and Drainage Paper 56 fixes as invariants — values that never change
per-parcel or per-run, as opposed to per-parcel parameters like albedo or crop
coefficients, which belong in packages/twin or packages/decision instead.
"""

from __future__ import annotations

#: Solar constant, MJ m-2 min-1. FAO-56 eq. 28.
SOLAR_CONSTANT_MJ_M2_MIN = 0.0820

#: Stefan-Boltzmann constant, MJ K-4 m-2 day-1. FAO-56 eq. 39.
STEFAN_BOLTZMANN_MJ_K4_M2_DAY = 4.903e-9

#: Standard atmospheric pressure at sea level, kPa. FAO-56 eq. 7 reference value.
STANDARD_ATMOSPHERIC_PRESSURE_KPA = 101.3

#: Specific heat at constant pressure, MJ kg-1 degC-1. FAO-56 eq. 8.
SPECIFIC_HEAT_AIR_MJ_KG_C = 1.013e-3

#: Ratio molecular weight of water vapour / dry air, dimensionless. FAO-56 eq. 8.
RATIO_MOLECULAR_WEIGHT_WATER_DRY_AIR = 0.622

#: Latent heat of vaporization, MJ kg-1. FAO-56 assumes this constant at ~2.45,
#: rather than its true (small) temperature dependence, per FAO-56 Box 6.
LATENT_HEAT_VAPORIZATION_MJ_KG = 2.45

#: Von Karman constant, dimensionless. FAO-56 eq. 4 (wind profile / aerodynamic
#: resistance derivations).
VON_KARMAN_CONSTANT = 0.41

#: Reference crop height, m. FAO-56 defines ET0 for a hypothetical grass
#: reference crop of this fixed height.
REFERENCE_CROP_HEIGHT_M = 0.12

#: Reference surface albedo, dimensionless. FAO-56 eq. 38, fixed for the grass
#: reference surface (not the same as a real crop's albedo).
REFERENCE_ALBEDO = 0.23

#: Bulk surface resistance of the reference crop, s m-1. FAO-56 Box 5, fixed
#: value baked into the FAO-56 form of the Penman-Monteith equation.
REFERENCE_SURFACE_RESISTANCE_S_M = 70.0

#: Height at which wind speed is standardized, m. FAO-56 eq. 47 wind speed
#: correction assumes measurements are converted to this height.
WIND_MEASUREMENT_HEIGHT_STANDARD_M = 2.0

#: Absolute zero offset, degC to Kelvin.
KELVIN_OFFSET_C = 273.16

#: Mean solar exo-atmospheric radiation seconds-per-day conversion constant used
#: throughout FAO-56 Chapter 3 (radiation section), unitless day fraction helper.
SECONDS_PER_DAY = 86400

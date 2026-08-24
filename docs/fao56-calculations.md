# FAO-56 and Physical Model Calculations

Complete, explanatory reference for every thermodynamic, hydrological, and radar-physics
calculation this system performs. Written to teach, not just to list formulas — read this
before implementing any function under `packages/twin/` or `packages/etl/`.

Primary source for Sections 1-9: **Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998).
"Crop evapotranspiration — Guidelines for computing crop water requirements." FAO Irrigation
and Drainage Paper 56.** Sources for Sections 10-13 are cited inline.

Units follow `CLAUDE.md` rule 5 throughout: **soil moisture in m3/m3, water depth in mm, time
in UTC.** Every formula below states the unit of its output explicitly — do not carry a bare
number between functions without checking this.

---

## 1. Extraterrestrial radiation (Ra)

**Physical meaning.** Ra is the solar radiation that would reach a horizontal surface at the
top of the atmosphere, with no atmosphere in the way. It depends only on the earth-sun
geometry — latitude, time of year, time of day — never on local weather. Every downstream
radiation term is expressed as a fraction or modification of this astronomical ceiling.

**Solar declination (δ)** — the angle of the sun relative to the equatorial plane, which is
why day length and sun angle vary through the year:

```
δ = 0.409 · sin(2π/365 · J − 1.39)          [rad]
```

where `J` is the day of the year (1-365/366).

**Inverse relative distance Earth-Sun (dr)** — the orbit is elliptical, so solar output at the
top of the atmosphere varies slightly through the year:

```
dr = 1 + 0.033 · cos(2π/365 · J)             [dimensionless]
```

**Sunset hour angle (ωs)** — the hour angle at which the sun sets, derived from latitude `φ`
(radians, positive north) and declination:

```
ωs = arccos(−tan(φ) · tan(δ))                [rad]
```

**Extraterrestrial radiation (daily, Ra):**

```
Ra = (24·60/π) · Gsc · dr · [ωs·sin(φ)·sin(δ) + cos(φ)·cos(δ)·sin(ωs)]
                                              [MJ m-2 day-1]
```

where `Gsc = 0.0820 MJ m-2 min-1` is the solar constant.

**Code identifiers:** `Ra`, `delta_solar` (δ, distinct from the vapor-pressure-curve slope
`Delta` in Section 5 — do not collide these names), `dr`, `omega_s`.

---

## 2. Net radiation (Rn = Rns − Rnl)

**Physical meaning.** Rn is the actual energy balance at the crop surface: incoming shortwave
(visible/near-IR sunlight) minus what is reflected, minus the net longwave (thermal infrared)
lost to the sky. Rn is the energy input term driving evaporation — no net radiation, no
evapotranspiration, regardless of how dry or windy the air is.

### 2.1 Net shortwave radiation (Rns)

```
Rns = (1 − α) · Rs                           [MJ m-2 day-1]
```

`Rs` is measured or estimated incoming solar radiation; `α = 0.23` is the reference albedo
(the standard FAO-56 hypothetical grass reference crop).

If `Rs` is not measured directly (the common case with API-sourced weather), it is estimated
from the Ångström formula using sunshine duration, or — more relevant to this system, which
draws forcing from reanalysis/forecast APIs (see `decisions/weather-forcing-split.md`) — from
the shortwave radiation field the weather provider already outputs (ERA5-Land: `ssrd`;
Open-Meteo: `shortwave_radiation`). **Do not re-derive Rs from sunshine hours when the
provider already supplies it** — that estimation path exists only for stations without a
pyranometer.

### 2.2 Net longwave radiation (Rnl)

**Physical meaning.** Every surface radiates thermal infrared according to its temperature
(Stefan-Boltzmann). Rnl is the *net* loss: outgoing longwave from the surface minus incoming
longwave from the atmosphere. It is reduced by cloud cover (clouds radiate back) and by low
humidity is *increased* (dry air radiates less back down).

```
Rnl = σ · [(Tmax,K^4 + Tmin,K^4)/2] · (0.34 − 0.14·√ea) · (1.35·Rs/Rso − 0.35)
                                              [MJ m-2 day-1]
```

- `σ = 4.903e-9 MJ K-4 m-2 day-1` — Stefan-Boltzmann constant
- `Tmax,K`, `Tmin,K` — daily max/min air temperature in **Kelvin**
- `ea` — actual vapor pressure, kPa (Section 5) — the humidity correction term
- `Rso` — clear-sky solar radiation, `Rso = (0.75 + 2e-5·z)·Ra`, where `z` is station elevation
  in metres — the cloudiness correction term (`Rs/Rso` capped at 1.0)

### 2.3 Net radiation

```
Rn = Rns − Rnl                               [MJ m-2 day-1]
```

**Code identifiers:** `Rns`, `Rnl`, `Rn`, `Rs`, `Rso`, `alpha_albedo`.

---

## 3. Soil heat flux (G)

**Physical meaning.** Some of the net radiation goes into heating the soil itself rather than
evaporating water. Over a full day this is usually a small correction because daytime heating
and nighttime release largely cancel.

**Daily timestep (the standard case for this system — see `open-decisions.md`, processing
tempo is daily for satellite/soil, hourly only for weather forcing):**

```
G ≈ 0                                        [MJ m-2 day-1]
```

FAO-56 states G is negligible relative to Rn for daily calculations and is set to zero unless
a specific soil temperature record justifies otherwise.

**Hourly/sub-daily timestep** (relevant only if a future phase computes ET0 at sub-daily
resolution from the hourly weather forcing):

```
G_hour_day   = 0.1 · Rn        (daytime, Rn > 0)      [MJ m-2 hour-1]
G_hour_night = 0.5 · Rn        (nighttime, Rn ≤ 0)     [MJ m-2 hour-1]
```

**Code identifiers:** `G` (always present in the ET0 function signature for readability and
future-proofing, defaulted to `0.0` at daily timestep).

---

## 4. Psychrometric constant (γ)

**Physical meaning.** γ links the psychrometer's temperature reading to vapor pressure — it
expresses how much the air's capacity to hold water vapor changes per degree of temperature
change, given atmospheric pressure. It is lower at altitude (thinner air), which is why the
same drop in wet-bulb temperature means less humidity change at altitude than at sea level.

```
γ = (cp · P) / (ε · λ) ≈ 0.665e-3 · P         [kPa °C-1]
```

- `cp = 1.013e-3 MJ kg-1 °C-1` — specific heat of moist air at constant pressure
- `ε = 0.622` — ratio of molecular weight of water vapor to dry air
- `λ = 2.45 MJ kg-1` — latent heat of vaporization (taken as constant at ~20°C; FAO-56 accepts
  this simplification for the ET0 standard)
- `P` — atmospheric pressure, kPa, from station elevation `z` (metres):

```
P = 101.3 · ((293 − 0.0065·z) / 293)^5.26     [kPa]
```

**Code identifiers:** `gamma_psychro`, `P_atm`.

---

## 5. Vapor pressure terms (es, ea, Δ)

**Physical meaning.** `es` (saturation vapor pressure) is how much water vapor the air *could*
hold at a given temperature if fully saturated — it rises steeply and nonlinearly with
temperature, which is the physical reason hot air dries things faster. `ea` (actual vapor
pressure) is how much water vapor is *actually* present, derived from humidity. The gap
`(es − ea)` is the vapor pressure deficit — the real driving force pulling moisture out of a
leaf or a wet soil surface. `Δ` is the slope of the es(T) curve — how sensitive `es` is to a
small temperature change, needed because Penman-Monteith linearizes around the mean
temperature.

### 5.1 Saturation vapor pressure at temperature T

```
e°(T) = 0.6108 · exp(17.27·T / (T + 237.3))   [kPa], T in °C
```

Mean saturation vapor pressure over the day, using max/min separately (not the mean
temperature, because `e°` is nonlinear and using `T_mean` underestimates `es`):

```
es = (e°(Tmax) + e°(Tmin)) / 2                [kPa]
```

### 5.2 Actual vapor pressure

From relative humidity (the common case with weather API data providing RHmax/RHmin or a
single RH):

```
ea = (e°(Tmin)·RHmax/100 + e°(Tmax)·RHmin/100) / 2   [kPa]
```

If only mean RH is available (lower-quality input, flag `data_quality` accordingly per the
`schemas.md` convention of never silently upgrading uncertain inputs):

```
ea = RHmean/100 · (e°(Tmax) + e°(Tmin))/2     [kPa]
```

If dewpoint temperature `Tdew` is provided directly by the weather source instead of RH (both
ERA5-Land and Open-Meteo can supply this) — the more numerically stable path, preferred when
available:

```
ea = e°(Tdew)                                 [kPa]
```

### 5.3 Slope of the saturation vapor pressure curve

Evaluated at mean daily temperature `T = (Tmax + Tmin)/2`:

```
Δ = 4098 · e°(T) / (T + 237.3)^2              [kPa °C-1]
```

**Code identifiers:** `es`, `ea`, `Delta_vp` (distinct from `delta_solar` in Section 1),
`e_sat` (the `e°(T)` helper function).

---

## 6. Wind speed adjustment to 2 m (u2)

**Physical meaning.** Wind removes the saturated air layer immediately above a wet surface,
exposing it to drier air and sustaining evaporation — this is the aerodynamic term. Wind speed
is height-dependent (it is slower near the ground due to surface friction), so a measurement
at any other height must be normalized to the FAO-56 reference height of 2 m before use.

```
u2 = uz · 4.87 / ln(67.8·z − 5.42)            [m s-1]
```

where `uz` is wind speed (m/s) measured at height `z` (metres) above ground. Most automated
weather stations and reanalysis products report at 10 m, giving the common case `z = 10`:

```
u2 = u10 · 4.87 / ln(67.8·10 − 5.42) ≈ u10 · 0.748
```

**Code identifiers:** `u2`, `uz`, `wind_height_m`.

---

## 7. FAO-56 Penman-Monteith reference evapotranspiration (ET0)

**Physical meaning.** ET0 is the evapotranspiration rate of a hypothetical, well-watered,
uniform grass reference surface (0.12 m tall, albedo 0.23, fixed surface resistance) under the
given weather. It is not the actual crop's water use — it is a weather-only "evaporative
demand" benchmark that every crop's actual ET is scaled from via `Kc` (Section 8). This is the
method selected for this project (Penman-Monteith, full form — see conversation record; the
simplified/empirical alternatives were explicitly rejected in favour of full accuracy).

```
        0.408·Δ·(Rn − G) + γ·(900/(T+273))·u2·(es − ea)
ET0 = ─────────────────────────────────────────────────────    [mm day-1]
              Δ + γ·(1 + 0.34·u2)
```

**Term-by-term reading:**

- `0.408·Δ·(Rn − G)` — the **radiation (energy-driven) term**. `0.408 = 1/λ` converts energy
  units (MJ m-2 day-1) to water depth units (mm day-1). This dominates on calm, sunny days.
- `γ·(900/(T+273))·u2·(es − ea)` — the **aerodynamic (wind/humidity-driven) term**. `900` is a
  standard constant folding in the reference crop's aerodynamic resistance and unit
  conversions; `T` is mean daily air temperature in °C. This dominates on windy, dry days.
- `Δ + γ·(1 + 0.34·u2)` — the shared denominator combining both terms via the psychrometric
  constant and slope, weighted by the reference surface's fixed 70 s/m stomatal resistance
  (folded into the `0.34·u2` coefficient).

**Inputs required, all daily:** `Tmax`, `Tmin` (°C), `RH` (or `Tdew`), `u2` (m/s, adjusted),
`Rs` or components to derive it, station `z` (elevation, m) and `φ` (latitude, rad) for `Ra`.

**Output unit: mm day-1.** This is a water depth per unit time — matches CLAUDE.md's water
depth convention directly; no further conversion needed before it enters the water balance.

**Code identifier:** `ET0`.

---

## 8. Crop coefficients — single Kc and dual Kc (Kcb + Ke)

**Physical meaning.** ET0 describes only the reference grass. A real crop differs in height,
canopy resistance, and ground cover, and the soil surface between plants also evaporates
independently of the crop. The crop coefficient scales ET0 up or down to the actual crop's
water use.

### 8.1 Single crop coefficient (simple form, not used in Phase 1 bucket model)

```
ETc = Kc · ET0                                [mm day-1]
```

`Kc` here lumps transpiration and soil evaporation into one time-varying curve (typically
tabulated by FAO-56 for each crop's initial/mid/late growth stages). This form is coarser:
it cannot represent a wetting event on bare/sparse soil raising ET sharply for a day or two
independent of the crop stage.

### 8.2 Dual crop coefficient (Kcb + Ke) — **the method this system uses**

`docs/modules.md` names `packages/twin/models/bucket.py` explicitly as "FAO-56 dual crop
coefficient water balance (Phase 1)" — this is the form that module implements.

```
ETc = (Kcb·Ks + Ke) · ET0                     [mm day-1]
```

Splitting the single `Kc` into two independently-varying components:

- **Kcb — basal crop coefficient.** Transpiration through the plant alone, assuming the soil
  surface is dry but the root zone is adequately watered. Varies smoothly with growth stage
  (initial → development → mid-season → late-season, tabulated per crop in FAO-56 Table 12,
  adjusted for local climate via the standard wind/humidity correction).
- **Ke — soil evaporation coefficient.** Evaporation from the exposed and/or wetted soil
  fraction, driven by how recently and how much the surface was wetted (rain or irrigation)
  and how much energy reaches bare soil through the canopy. This is why applied-water records
  (`IRRIGATION_LOG`) feed directly into the ET calculation, not just into the water balance —
  a wetting event visibly raises `Ke` for the following days.
- **Ks — water stress coefficient** (Section 9) — multiplies `Kcb` only, because water stress
  suppresses transpiration through stomatal closure; it does not suppress evaporation from a
  wet soil surface the same way.

**Ke computation (FAO-56 Ch. 7):**

```
Ke = min(Kr · (Kc_max − Kcb),  few · Kc_max)  [dimensionless, ≥ 0]
```

- `Kc_max` — upper limit on `Kcb + Ke` set by energy available at the surface (function of crop
  height and `u2`, `RHmin`; FAO-56 eq. 72)
- `few` — exposed and wetted soil fraction, `few = min(1 − fc, fw)`, where `fc` is fraction of
  ground covered by canopy (from crop stage or, in this system, S2-derived fCover — the "hard
  dependency for the vegetation correction" noted in `modules.md`) and `fw` is the fraction of
  soil surface wetted by irrigation/rain — **the same `fw` that is a fitted parameter in
  `PARCEL_ADAPTATION`** per `decisions/applied-water-measurement.md`. This is the direct bridge
  between the irrigation-method decision and the crop-water-use calculation: under subsurface
  drip `fw` is small, so `few` and therefore `Ke` stay small even after a large irrigation
  event, because the wetting never reaches the exposed surface.
- `Kr` — dimensionless evaporation reduction coefficient, tracking depletion of a shallow
  surface soil layer (the "evaporation layer", typically 10-15 cm deep, tracked via its own
  small water balance separate from the root-zone balance in Section 9):

```
Kr = (TEW − De) / (TEW − REW)      if De > REW,  else Kr = 1
```

  `TEW` = total evaporable water in the surface layer (mm), `REW` = readily evaporable water
  (mm, the "stage 1" energy-limited portion), `De` = cumulative depletion of the surface layer
  since the last wetting (mm) — its own daily-updated depletion tracker running parallel to the
  root-zone `Dr` in Section 9.

**Code identifiers:** `Kcb`, `Ke`, `Kr`, `Kc_max`, `few`, `fc`, `TEW`, `REW`, `De`, `ETc`.

---

## 9. Root zone water balance (TAW, RAW, Dr, Ks)

**Physical meaning.** This is the FAO-56 "bucket model" itself — a single well-mixed reservoir
representing the root zone, filled by irrigation/rain and drained by `ETc` and deep
percolation. It is the concrete algorithm behind `packages/twin/models/bucket.py`, and per
`docs/architecture.md` Section 8 ("Degradation ladder"), it is the **fallback model at levels
L2 and L3** — not a throwaway Phase 1 scaffold — so it must be implemented to production
standard, not as a placeholder.

### 9.1 Total and readily available water

```
TAW = 1000 · (θ_FC − θ_WP) · Zr               [mm]
RAW = p · TAW                                 [mm]
```

- `θ_FC` — field capacity, m3/m3 (upper bound of plant-available water; matches CLAUDE.md's
  volumetric soil moisture convention directly)
- `θ_WP` — wilting point, m3/m3 (lower bound; below this the crop cannot extract further water)
- `Zr` — root zone depth, metres (the `1000·` factor converts metres of soil times a
  dimensionless volumetric fraction into millimetres of water — a unit-conversion step worth
  stating explicitly because it is the one place metres and millimetres meet in this document)
- `p` — depletion fraction for no stress (crop- and ET-rate-dependent, typically 0.3-0.7,
  FAO-56 Table 22), the fraction of TAW that can be depleted before stress begins

### 9.2 Root zone depletion (the state variable, updated daily)

```
Dr(t) = Dr(t-1) − P_eff(t) − I(t) + ETc(t) + DP(t)
```

where all terms are in mm/day:
- `P_eff` — effective precipitation reaching the root zone (rainfall minus runoff, `Dr` cannot
  go below 0 — excess is deep percolation, see `DP` below)
- `I` — irrigation depth actually applied. **This is where `IRRIGATION_LOG.measured_depth_mm`
  enters the twin** — the "zone-average, no `fw` applied" value defined in `schemas.md`, since
  `Dr` is a zone-average bucket. `fw` is applied only inside `Ke`/`few` (Section 8), never
  here, matching `schemas.md`'s design rule 2 ("log records fact, not interpretation").
- `ETc` — crop evapotranspiration (Section 8), draining the bucket
- `DP` — deep percolation, occurring only when the bucket would overfill: if
  `Dr(t-1) − P_eff − I < 0`, the negative amount is `DP` and `Dr` is clamped to 0

`Dr` is bounded: `0 ≤ Dr ≤ TAW`. `Dr = 0` means the root zone is at field capacity; `Dr = TAW`
means the crop has extracted all available water (permanent wilting point reached).

**Conversion to volumetric moisture, when needed for comparison against SAR-observed or
SMAP-observed θ:**

```
θ(t) = θ_FC − Dr(t) / (1000 · Zr)             [m3/m3]
```

This is the explicit bridge between the mm-denominated bucket state and the m3/m3-denominated
moisture state that the PINN (Section 11) and the observation operator (Section 12) both work
in — the two state representations of the same physical quantity, related by root depth and
field capacity, and this is the formula that converts between them.

### 9.3 Water stress coefficient

```
Ks = (TAW − Dr) / (TAW − RAW)      if Dr > RAW,  else Ks = 1
```

`Ks = 1` while depletion stays within the "readily available" fraction (no stress, crop
transpires at the potential rate `Kcb·ET0`); it falls linearly toward 0 as `Dr` approaches
`TAW`. This is the term that feeds back into Section 8's `ETc = (Kcb·Ks + Ke)·ET0` — a
water-stressed crop transpires less, which is exactly the closed loop a water-balance model is
for.

**Code identifiers:** `TAW`, `RAW`, `Dr`, `Ks`, `theta_FC`, `theta_WP`, `Zr`, `p_depletion`,
`P_eff`, `DP`, `theta_from_Dr`.

---

## 10. Unit conventions — summary table

Restating `CLAUDE.md` rule 5 concretely against every quantity defined above, since a
mismatched unit here is a silent correctness bug, not a crash:

| Quantity | Unit | Convention source |
|---|---|---|
| `ET0`, `ETc`, `TAW`, `RAW`, `Dr`, `De`, `TEW`, `REW`, `P_eff`, `DP`, `I` | mm (or mm/day as a rate) | CLAUDE.md rule 5 — water depth is mm |
| `θ_FC`, `θ_WP`, `θ(t)` (bucket and PINN state) | m3/m3 | CLAUDE.md rule 5 — soil moisture is volumetric |
| `Rn`, `Rns`, `Rnl`, `Ra`, `Rs`, `Rso`, `G` | MJ m-2 day-1 | FAO-56 native energy unit |
| `T`, `Tmax`, `Tmin`, `Tdew` | °C for all formula inputs; **Kelvin only inside `Rnl`'s σT^4 term** | FAO-56 eq. 39 |
| `es`, `ea`, `Δ`, `γ`, `P_atm` | kPa (kPa °C-1 for `Δ`, `γ`) | FAO-56 Ch. 3 |
| `u2`, `uz` | m s-1 | FAO-56 eq. 47 |
| All timestamps | UTC, timezone-aware | CLAUDE.md rule 5 — local time only at the edge layer |
| `Zr` (root depth) | **metres** — the one exception; converted to mm via the `1000·` factor in TAW/θ formulas, never left ambiguous | Section 9.1 |

---

## 11. Gaps found and filled

This section is a reverse gap analysis: every place across `docs/architecture.md`,
`docs/modules.md`, `docs/schemas.md`, `docs/decisions/*.md`, `docs/open-decisions.md`,
`docs/delivery-plan.md`, and `docs/superseded-decisions.md` where a physical calculation is
referenced conceptually but never written out as a concrete formula. Each gap is filled below.
Nothing in `docs/decisions/` was edited — those files record accepted decisions and their
Status/Decision/Rationale sections are left untouched, per `CLAUDE.md` rule 1.

### 11.1 Gap: the Water Cloud Model (WCM) forward operator

**Where referenced, never made concrete:** `decisions/observation-operator.md` ("an embedded
**differentiable WCM / Oh-Dubois** model produces `sigma0_predicted`" — no equation given);
`decisions/pooling-strategy.md` (`WCM A/B` listed as a fitted parameter, no equation);
`decisions/ml-layering.md` (Layer B "PINN with embedded WCM" — no equation);
`docs/modules.md` ("The WCM forward operator is embedded and must be autodiff-compatible" —
no equation); `docs/architecture.md` Section 2 diagram (`TWIN[... embedded WCM ...]` — no
equation).

**Filled — Water Cloud Model, standard form (Attema & Ulaby, 1978), attenuation-through-vegetation
decomposition:**

The observed radar backscatter is modelled as vegetation backscatter plus soil backscatter
attenuated by the vegetation layer above it:

```
σ0_predicted = σ0_veg + τ² · σ0_soil          [linear power, m2/m2, or dB after 10·log10]
```

**Vegetation contribution:**

```
σ0_veg = A · V1 · cos(θ) · (1 − τ²)           [linear power]
```

**Two-way vegetation transmissivity (attenuation):**

```
τ² = exp(−2·B·V2 / cos(θ))                    [dimensionless, 0-1]
```

**Soil contribution** — this is the term the PINN's `theta(z,t)` output must drive, via a
soil backscatter model (Oh model or Dubois model — either is a closed-form, differentiable
function of volumetric moisture `θ`, surface roughness `s` (RMS height, cm), and incidence
angle `θ_inc`; the specific choice between Oh and Dubois is left as an implementation-level
selection, not a re-opened architecture decision, since `observation-operator.md` only commits
to "WCM / Oh-Dubois" as a family, not a specific member):

```
σ0_soil = f_soil(θ(z=0,t), s, θ_inc)          [linear power]
```

**Where:**
- `θ` (angle) — radar incidence angle, degrees/radians, fixed per sensor geometry (Sentinel-1
  IW mode: ~29-46°)
- `V1`, `V2` — vegetation descriptors, commonly both taken as a single vegetation water content
  or LAI/fCover-derived proxy in simplified WCM implementations (`V1 = V2 = V`, e.g. LAI); this
  system already has S2-derived LAI/fCover as a "hard dependency for the vegetation correction"
  (`modules.md`), which is exactly the input `V` needs
- `A`, `B` — the two learnable WCM coefficients named throughout the decision records
  (`pooling-strategy.md` Layer 1: `WCM A/B`); `A` scales vegetation backscatter magnitude, `B`
  controls attenuation strength — both must remain inside the autodiff graph, since
  `observation-operator.md` requires "no non-closed-form step" and end-to-end learnability of
  `A, B`
- `θ(z=0,t)` — the PINN's surface-layer moisture output; this is the exact seam where
  Section 9's bucket `θ(t)` (fallback model) and the PINN's `theta(z,t)` (primary model) both
  connect to the same observation operator, keeping the two models' outputs comparable

**Loss connection** (already given in `observation-operator.md`'s loss skeleton, restated here
with the operator made concrete): `L(sigma0) = ‖σ0_observed − σ0_predicted‖`, evaluated only
where Layer A (`ml-layering.md`) has classified the observation as usable, with `R` (EnKF
observation error covariance, Section 13) set inversely proportional to Layer A's soft
usability weight.

### 11.2 Gap: 1D Richards equation (PINN physics residual)

**Where referenced, never made concrete:** `docs/modules.md` ("Second-order autodiff is
required for the Richards residual"); `decisions/observation-operator.md` (`L_richards` in
the loss skeleton, no equation); `decisions/pooling-strategy.md` (van Genuchten parameters
`theta_r, theta_s, alpha, n, Ks` listed as unknowns, no equation connecting them to state);
`docs/architecture.md` Section 1 ("the loss embeds ... 1D Richards mass conservation" — no
equation).

**Filled — 1D vertical Richards equation, mixed form:**

```
∂θ/∂t = ∂/∂z [ K(θ) · (∂ψ/∂z + 1) ] − S(z,t)
```

- `θ(z,t)` — volumetric moisture, m3/m3, the PINN's primary output (matches CLAUDE.md
  convention directly)
- `z` — depth, m, positive downward
- `ψ(θ)` — matric potential (soil water pressure head), m, a function of `θ` via the water
  retention curve (below)
- `K(θ)` — unsaturated hydraulic conductivity, m/day, also a function of `θ`
- `S(z,t)` — root water uptake sink term, m3 m-3 day-1 — this is the PINN-side analog of
  Section 9's `ETc` term; a common closed form distributes potential transpiration
  (`Kcb·Ks·ET0` from Section 8/9) across the root profile with a root density weighting
  function, so that integrating `S(z,t)` over the root depth recovers the same transpiration
  flux the bucket model computes as a lump sum — this is the physical link that lets the PINN
  and the bucket model be cross-validated against each other in the degradation ladder
  (`architecture.md` Section 8, L2/L3)

**Van Genuchten-Mualem closure** (the standard pair of constitutive relations that make the
equation solvable — these supply `ψ(θ)` and `K(θ)`, and are exactly the "van Genuchten priors"
named in `observation-operator.md`'s loss skeleton as `L(van Genuchten priors)`):

```
Se(θ) = (θ − θr) / (θs − θr)                  [effective saturation, 0-1]

ψ(Se) = −(1/α) · (Se^(−1/m) − 1)^(1/n),   m = 1 − 1/n     [m, water retention curve]

K(Se) = Ks · Se^L · [1 − (1 − Se^(1/m))^m]^2  [m/day, hydraulic conductivity function]
```

Free parameters, all per zone/parcel: `θr` (residual moisture), `θs` (saturated moisture,
≈ porosity), `α` (inverse air-entry pressure, m-1), `n` (pore-size distribution shape,
dimensionless), `Ks` (saturated hydraulic conductivity, m/day — the same `Ks` multiplied by
`Ks_mult` in `PARCEL_ADAPTATION`, distinct in meaning from the water-stress `Ks` of Section
9.3; both are named `Ks` in FAO-56/van Genuchten literature independently — **implementations
must disambiguate these two `Ks` with distinct code identifiers**, e.g. `Ks_vg` (saturated
conductivity) vs `Ks_stress` (Section 9.3), to avoid a name collision that silently corrupts a
formula), `L` (pore connectivity, typically fixed at 0.5, Mualem's original value).

**Why this is stiff (context for `docs/modules.md`'s "3-5x cost per step" note):** `K(θ)` and
`ψ(θ)` both vary by orders of magnitude between dry and saturated soil, especially near `θs`
where `K(θ)` rises extremely steeply — this is the stated reason loss weights must be
self-adaptive rather than hand-tuned, and why second-order autodiff (needed for the residual
of a second-order PDE in `z`) is expensive.

**Boundary and initial conditions** (the `L_boundary_conditions` and `L_initial_conditions`
terms in the loss skeleton, made concrete):

- **Top (surface) boundary, z=0:** flux-type, `q(0,t) = P_eff(t) + I(t) − E_soil(t)`, i.e. net
  infiltration flux equals effective precipitation plus applied irrigation minus soil
  evaporation — `E_soil` is the PINN-side counterpart of Section 8's `Ke·ET0` term, so
  `IRRIGATION_LOG.measured_depth_mm` is again the concrete data source for `I(t)`, exactly as
  in Section 9.2.
- **Bottom boundary, z=Zmax:** typically free drainage, `∂ψ/∂z = 0` (unit hydraulic gradient),
  a standard simplification when no water table data exists — matches this system's
  zero-in-field-sensor premise.
- **Initial condition, t=0:** `θ(z,0)` from the previous day's EnKF-updated state (Section 13)
  — the PINN is not solved cold each day, it continues from the assimilated state.

**Code identifiers:** `theta_z_t`, `psi_vg`, `K_vg`, `theta_r`, `theta_s_vg`, `alpha_vg`,
`n_vg`, `Ks_vg`, `L_mualem`, `S_uptake`, `L_richards` (the PDE residual loss term).

### 11.3 Gap: EnKF assimilation update equations

**Where referenced, never made concrete:** `docs/modules.md` (`assimilation/  EnKF state +
latent update` — directory named, no equations); `decisions/pooling-strategy.md` ("Only state +
z are updated (EnKF, sub-second)" — no equations); `decisions/ml-layering.md` (Layer C:
"State + z + fw update — EnKF, R set by layer A" — no equations); `docs/architecture.md`
Section 5 (`TWIN->>TWIN: EnKF update (state + z)` in the sequence diagram — no equations);
`open-decisions.md` ("Online update method... Recommendation: EnKF" — a recommendation, not
yet a written-out method — left as-is, since this remains an **open decision**, not settled;
the equations below are the standard EnKF form, provided so the eventual implementation has a
concrete reference, and do not resolve or close the open decision itself).

**Filled — Ensemble Kalman Filter, standard form, applied to the augmented state
`x = [θ(z,t); z_latent]` (soil moisture profile stacked with the parcel's Layer 1 latent
vector, since `pooling-strategy.md` states both are updated together):**

**Forecast step** — propagate each of `N` ensemble members forward one day through the PINN
(or bucket model, at degradation levels L2/L3):

```
x_i^f(t) = M(x_i^a(t−1)) + w_i,   w_i ~ N(0, Q),   i = 1..N
```

`M(·)` is the forward model (PINN or bucket), `Q` is process noise covariance (accounts for
forcing/model uncertainty), `x_i^a(t−1)` is the previous day's analysis (updated) ensemble.

**Observation prediction** — pass each forecast member through the observation operator
(Section 11.1's WCM):

```
y_i^f = H(x_i^f) = σ0_predicted(x_i^f)
```

**Ensemble statistics:**

```
Pxy = (1/(N−1)) · Σ_i (x_i^f − x̄^f)(y_i^f − ȳ^f)^T      [cross-covariance]
Pyy = (1/(N−1)) · Σ_i (y_i^f − ȳ^f)(y_i^f − ȳ^f)^T      [innovation covariance]
```

**Kalman gain:**

```
K = Pxy · (Pyy + R)^-1
```

`R` is the observation error covariance — **this is precisely the quantity Layer A
(`ml-layering.md`) sets via its soft usability weights**: a high-confidence SAR observation
gets small `R` (trusted, pulls the state strongly toward the observation); a marginal
observation (dense vegetation, near-layover) gets large `R` (the update barely moves the
state). This is the concrete mechanism behind the phrase "R set by layer A."

**Analysis (update) step**, per ensemble member, with perturbed observations (standard
stochastic EnKF, avoids ensemble collapse):

```
x_i^a(t) = x_i^f(t) + K · (σ0_observed(t) + ε_i − y_i^f),   ε_i ~ N(0, R)
```

**Posterior state estimate and uncertainty**, reported downstream to the decision engine
(`docs/architecture.md` Section 5: "TWIN->>DEC: state + uncertainty"):

```
θ̄(z,t) = mean_i(x_i^a)[θ component]           [m3/m3]
σ_θ(z,t) = std_i(x_i^a)[θ component]           [m3/m3]
```

`σ_θ` is exactly the uncertainty term that drives the degradation ladder's confidence level
(`architecture.md` Section 8) and the recipe's `confidence: normal/low` field
(`architecture.md` Section 4).

**On days with no usable observation** (Layer A rejects everything, or no S1 scene): the
update step is skipped entirely and only the forecast step runs — `x_i^a(t) = x_i^f(t)` — which
is the formal reason uncertainty widens under "L1 Stale observation" in the degradation ladder:
with no correction, ensemble spread grows unchecked through repeated forecast steps.

**Code identifiers:** `ensemble_forecast`, `Q_process_noise`, `R_obs_noise` (set by Layer A
output), `kalman_gain`, `theta_mean`, `theta_std`, `z_latent_mean`, `z_latent_std`.

### 11.4 Gap: `architecture.md` Section 12 "Unresolved slots" — assimilation implementation

`architecture.md` Section 12 lists "Assimilation implementation" as blocked on the (still open)
"Online update method" decision. No formula edit was made to `architecture.md` itself — the
slot correctly reflects that this remains unresolved as an *architectural choice* (EnKF vs
particle filter vs weekly batch, per `open-decisions.md`), even though Section 11.3 above now
supplies the concrete EnKF equations that would apply *if and when* EnKF is confirmed. Adding
the formulas here rather than editing `architecture.md` keeps the open-decision status honest:
a formula existing in this reference doc does not constitute the decision being made.

### 11.5 No gap: applied-water depth conversion

`schemas.md` defines `measured_depth_mm = volume_l / area_m2` with the explicit note "No `fw`
applied." This is already a complete, concrete formula — no gap. It is restated in Section 9.2
above only to show where it enters the water balance equation, not because it was missing.

### Flagged for decision-record follow-up

Not formula gaps — structural points noticed while cross-referencing the decision records
against the calculations above. Left as flags only; no decision file was edited.

1. **`Ks` name collision.** `pooling-strategy.md` and `open-decisions.md` both use `Ks` for van
   Genuchten saturated hydraulic conductivity, while `docs/architecture.md`/FAO-56 convention
   (Section 9.3 above) uses `Ks` for the water stress coefficient. These are different physical
   quantities that happen to share a symbol in the source literature they each come from. Not a
   documentation error — both usages are individually correct — but worth a one-line disambiguation
   note in whichever decision record or module docstring first introduces code-level naming, since
   the collision will otherwise reappear directly as a bug (two different meanings assigned to
   one variable name) rather than staying a documentation nuisance.
2. **WCM member choice (Oh vs Dubois) is unresolved at the implementation level.**
   `observation-operator.md` commits to the WCM/Oh-Dubois family but not a specific soil
   backscatter sub-model. This is small enough that it likely does not need its own decision
   record (unlike the items in `open-decisions.md`, which are described as blocking), but
   whoever implements `packages/twin/models/pinn.py` will need to pick one and should record the
   choice, even briefly, since it affects `A`/`B` fitted values and is not swappable later
   without refitting `PARCEL_ADAPTATION`.
3. **Root water uptake sink function `S(z,t)` (Section 11.2) has no named decision record.** It
   is a standard, low-risk modelling choice (root-density-weighted distribution of transpiration
   demand), but it is the one piece of the Richards equation with no existing architectural
   anchor anywhere in `docs/`. Likely fine to settle as an implementation detail inside
   `packages/twin/models/pinn.py` rather than a decision record, given its narrow scope.

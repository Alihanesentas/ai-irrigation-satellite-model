"""FAO-56 dual crop coefficient bucket water balance — `docs/modules.md`
names this module explicitly: "FAO-56 dual crop coefficient water balance
(Phase 1)". Implements `agritwin_twin.interface.SoilModel`.

Per `docs/architecture.md` section 8 (degradation ladder), this is not a
throwaway Phase 1 scaffold — it is the **permanent fallback model at levels
L2 and L3** — so it is written to production standard: every term traces to
a numbered section of `docs/fao56-calculations.md`, and every simplification
relative to the full FAO-56 procedure is called out explicitly rather than
silently folded in.

Two interchangeable deep-percolation models (`BucketConfig.percolation_mode`):

- `"fao56_instant"` — the standard FAO-56 treatment (section 9.2): any
  depletion below zero (root zone above field capacity) drains completely
  within the same day, `Dr` clamped to 0. This is what FAO-56 itself
  specifies and is the correct default for exit-criterion comparability.
- `"van_genuchten"` — `percolation.py`'s free-drainage, van-Genuchten-K(theta)
  flux (section 11.2) in place of the instant-drain assumption: drainage is
  gradual and moisture-dependent, only becoming fast near saturation. This
  is the "how much of the applied/rain water actually reaches the roots,
  not just the surface" mechanism raised as a project requirement — a
  physically-motivated approximation of Richards' law without solving the
  full PDE (that remains Phase 3's PINN). The benchmark notebook runs both
  modes side by side for direct comparison.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from agritwin_core.units import DepthMM, VolumetricMoisture

from agritwin_twin import meteorology, percolation
from agritwin_twin.crops import CropParameters
from agritwin_twin.interface import DailyForcing, SoilState
from agritwin_twin.soils import SoilParameters

PercolationMode = Literal["fao56_instant", "van_genuchten"]


@dataclass(frozen=True, slots=True)
class BucketConfig:
    crop: CropParameters
    soil: SoilParameters
    latitude_rad: float
    elevation_m: float
    percolation_mode: PercolationMode = "fao56_instant"
    evaporation_layer_depth_m: float = 0.125
    """Ze, section 8.2 — FAO-56 typical range 0.10-0.15 m, midpoint default."""
    readily_evaporable_water_mm: float = 9.0
    """REW, FAO-56 Table 19 typical value for a medium-textured soil.
    Table 19 is texture-specific in the full standard; a single default is
    used here rather than a texture lookup — flagged as a simplification."""
    wetted_fraction: float = 1.0
    """`fw` — simplified to a constant here rather than the fitted,
    irrigation-method-dependent value `PARCEL_ADAPTATION.fw` becomes once
    real applied-water data exists (`docs/decisions/applied-water-measurement.md`).
    1.0 (full-surface wetting) is appropriate for rainfed evaluation; a real
    per-zone `fw` should replace this once irrigation events are simulated
    with a specific method."""
    runoff_fraction: float = 0.0
    """Fraction of precipitation lost to runoff before reaching the soil.
    0.0 (no runoff model) is a stated simplification — FAO-56's full runoff
    treatment requires curve-number/slope data this rule-based benchmark
    does not have."""
    stale_forcing_days_for_low_confidence: int = 5
    """Days `extrapolate()` (no fresh forcing) can run before `SoilState.confidence`
    drops to `"low"` — the bucket model's crude proxy for
    `docs/architecture.md` section 8's L1 "stale observation" level; see
    `SoilState.confidence` docstring."""


@dataclass(frozen=True, slots=True)
class BucketDiagnostics:
    """Every intermediate term from one `step()` call — not part of the
    `SoilModel` protocol's return value (`SoilState` stays deliberately
    narrow, matching what the decision engine actually needs), but exposed
    via `BucketModel.last_diagnostics` for the benchmark notebook, which
    plots ET0/ETc/Kcb/Ke/DP decomposition directly per
    `docs/fao56-calculations.md`'s "read this to teach, not just to list
    formulas" framing.
    """

    et0_mm: float
    kcb: float
    ke: float
    kr: float
    ks_stress: float
    etc_mm: float
    p_eff_mm: float
    deep_percolation_mm: float
    tew_mm: float
    de_mm: float
    taw_mm: float
    raw_mm: float
    root_depth_m: float
    ground_cover_fc: float
    few: float


class BucketModel:
    """Implements `agritwin_twin.interface.SoilModel` structurally (no
    inheritance needed, per that module's docstring)."""

    def __init__(
        self,
        config: BucketConfig,
        *,
        initial_dr_mm: float | None = None,
        initial_de_mm: float = 0.0,
    ) -> None:
        self.config = config
        root_depth_m = config.crop.root_depth_max_m
        taw = _taw_mm(config.soil, root_depth_m)
        self._dr_mm = taw * 0.3 if initial_dr_mm is None else initial_dr_mm
        self._de_mm = initial_de_mm
        self._days_since_forcing = 0
        self._state: SoilState | None = None
        self.last_diagnostics: BucketDiagnostics | None = None
        self._initialize_state(datetime.min)

    def _initialize_state(self, at: datetime) -> None:
        root_depth_m = self.config.crop.root_depth_max_m
        theta = self.config.soil.theta_fc - self._dr_mm / (1000 * root_depth_m)
        taw = _taw_mm(self.config.soil, root_depth_m)
        raw = self.config.crop.depletion_fraction_p * taw
        self._state = SoilState(
            valid_at=at,
            theta=VolumetricMoisture(max(0.0, min(1.0, theta))),
            theta_std=None,
            dr_mm=DepthMM(self._dr_mm),
            ks_stress=1.0,
            raw_mm=DepthMM(raw),
            taw_mm=DepthMM(taw),
            confidence="normal",
        )

    def state(self) -> SoilState:
        assert self._state is not None
        return self._state

    def step(self, forcing: DailyForcing, applied_water_mm: DepthMM) -> SoilState:
        crop = self.config.crop
        soil = self.config.soil
        day_of_year = forcing.date_utc.timetuple().tm_yday

        et0 = meteorology.reference_et0(
            day_of_year=day_of_year,
            latitude_rad=self.config.latitude_rad,
            elevation_m=self.config.elevation_m,
            tmax_c=forcing.tmax_c,
            tmin_c=forcing.tmin_c,
            rs_mj_m2_day=forcing.rs_mj_m2_day,
            wind_speed_ms=forcing.wind_speed_ms,
            wind_height_m=forcing.wind_height_m,
            tdew_c=forcing.tdew_c,
            rh_max_pct=forcing.rh_max_pct,
            rh_min_pct=forcing.rh_min_pct,
            rh_mean_pct=forcing.rh_mean_pct,
        ).et0.value

        root_depth_m = crop.root_depth_max_m
        taw = _taw_mm(soil, root_depth_m)
        raw = crop.depletion_fraction_p * taw
        tew = 1000 * (soil.theta_fc - 0.5 * soil.theta_wp) * self.config.evaporation_layer_depth_m
        rew = min(self.config.readily_evaporable_water_mm, tew)

        kcb = crop.kcb_at(day_of_year)
        fc = crop.ground_cover_at(day_of_year)
        u2 = meteorology.wind_speed_2m(forcing.wind_speed_ms, forcing.wind_height_m)
        rh_min = forcing.rh_min_pct if forcing.rh_min_pct is not None else 45.0
        kc_max = max(
            1.2 + (0.04 * (u2 - 2) - 0.004 * (rh_min - 45)) * (crop.plant_height_m / 3) ** 0.3,
            kcb + 0.05,
        )
        few = min(1 - fc, self.config.wetted_fraction)

        kr = 1.0 if self._de_mm <= rew else max(0.0, (tew - self._de_mm) / (tew - rew))
        ke = min(kr * (kc_max - kcb), few * kc_max)
        ke = max(0.0, ke)

        ks_stress = 1.0 if self._dr_mm <= raw else max(0.0, (taw - self._dr_mm) / (taw - raw))
        etc = (kcb * ks_stress + ke) * et0

        p_eff = forcing.precip_mm * (1 - self.config.runoff_fraction)
        irrigation_mm = applied_water_mm.value

        dr_before_drain = self._dr_mm - p_eff - irrigation_mm + etc

        if self.config.percolation_mode == "fao56_instant":
            deep_percolation = max(0.0, -dr_before_drain)
            dr_after = max(0.0, dr_before_drain)
        else:
            theta_before = soil.theta_fc - self._dr_mm / (1000 * root_depth_m)
            deep_percolation = percolation.van_genuchten_drainage_mm_per_day(theta_before, soil)
            dr_after = dr_before_drain + deep_percolation

        dr_new = max(0.0, min(taw, dr_after))

        surface_wetting = p_eff + irrigation_mm
        e_soil = ke * et0
        de_new = max(0.0, min(tew, self._de_mm - surface_wetting + e_soil))

        self._dr_mm = dr_new
        self._de_mm = de_new
        self._days_since_forcing = 0

        theta = soil.theta_fc - dr_new / (1000 * root_depth_m)
        theta_clamped = max(0.0, min(1.0, theta))

        self.last_diagnostics = BucketDiagnostics(
            et0_mm=et0,
            kcb=kcb,
            ke=ke,
            kr=kr,
            ks_stress=ks_stress,
            etc_mm=etc,
            p_eff_mm=p_eff,
            deep_percolation_mm=deep_percolation,
            tew_mm=tew,
            de_mm=de_new,
            taw_mm=taw,
            raw_mm=raw,
            root_depth_m=root_depth_m,
            ground_cover_fc=fc,
            few=few,
        )

        self._state = SoilState(
            valid_at=forcing.date_utc,
            theta=VolumetricMoisture(theta_clamped),
            theta_std=None,
            dr_mm=DepthMM(dr_new),
            ks_stress=ks_stress,
            raw_mm=DepthMM(raw),
            taw_mm=DepthMM(taw),
            confidence="normal",
        )
        return self._state

    def extrapolate(self, at: datetime) -> SoilState:
        """No fresh forcing available — freezes `theta`/`Dr` at their last
        value rather than guessing (CLAUDE.md rule 6: uncertainty resolves
        toward "do not irrigate", not toward an invented number), and
        degrades `confidence` to `"low"` once
        `stale_forcing_days_for_low_confidence` is exceeded. Crude proxy for
        `docs/architecture.md` section 8's L1 "stale observation" /
        L4 "serve last recipe until valid_until" — the real backbone
        residual-based detection is a Phase 3 concern (section 9 of
        `docs/architecture.md`).
        """
        self._days_since_forcing += 1
        assert self._state is not None
        confidence = (
            "low"
            if self._days_since_forcing > self.config.stale_forcing_days_for_low_confidence
            else self._state.confidence
        )
        self._state = SoilState(
            valid_at=at,
            theta=self._state.theta,
            theta_std=self._state.theta_std,
            dr_mm=self._state.dr_mm,
            ks_stress=self._state.ks_stress,
            raw_mm=self._state.raw_mm,
            taw_mm=self._state.taw_mm,
            confidence=confidence,
        )
        return self._state


def _taw_mm(soil: SoilParameters, root_depth_m: float) -> float:
    """TAW, section 9.1."""
    return 1000 * (soil.theta_fc - soil.theta_wp) * root_depth_m


__all__ = ["BucketConfig", "BucketDiagnostics", "BucketModel", "PercolationMode"]

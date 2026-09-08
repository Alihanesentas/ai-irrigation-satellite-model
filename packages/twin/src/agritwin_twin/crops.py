"""Per-crop FAO-56 parameter layer — the pluggable piece that lets the same
bucket-model engine (`models/bucket.py`) run for a different crop by swapping
one `CropParameters` object, per `docs/delivery-plan.md` Phase 2's "Kc from
crop tables; optional S2 NDVI refinement" and `docs/modules.md`'s
crop/cohort framing.

Two crops are parametrized for the project's pilot region (Manisa, western
Anatolia/Aegean Turkey — the same region named throughout `docs/` as the
Aegean/Mediterranean pilot terrain): **olive (zeytin)** and **sultana/table
grape (üzüm)**, Manisa's dominant grape type per literature (not wine grape).

Every numeric value below carries an inline source citation and, where the
source itself flags low confidence, an explicit note. **None of these are
project decisions in the `docs/decisions/` sense** — they are literature
defaults for a rule-based benchmark, expected to be superseded by locally
calibrated values (via S2 NDVI phenology tracking and real yield/ET
ground-truth) once real field data exists. Treat every value tagged
"literature-typical, needs local calibration" accordingly.

Primary sources:
- FAO-56 (Allen et al. 1998) Table 12 (Kc ini/mid/end, canopy height) and
  Table 22 (max root depth Zr, depletion fraction p) — fetched directly from
  fao.org for this module.
- Tapoco et al. (2014) and a Mediterranean eddy-covariance olive-orchard
  study (ScienceDirect, S0378377407002715) for the olive local-adjustment
  factor — see `OLIVE_MANISA.kcb_local_adjustment` docstring below.
- Manisa vineyard soil-survey literature (ResearchGate 366584164) for the
  representative soil texture used in `soils.py`, not repeated here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class Phenology(str, Enum):
    """How a crop's canopy behaves outside its defined ini/dev/mid/late
    growing-season window — see `CropParameters.kcb_at` for how each value
    is handled. FAO-56 Table 11's growth-stage lengths are written for
    annual field crops; neither olive nor grape is one, so both require this
    explicit extension rather than a direct table lookup (flagged by
    research as the lowest-confidence part of this module)."""

    EVERGREEN = "evergreen"
    """No true dormancy — canopy transpires year-round. Outside the defined
    season window, `Kcb` holds at `kcb_end` rather than dropping toward
    zero. Olive."""

    DECIDUOUS = "deciduous"
    """Leaf-off dormant period. Outside the defined season window, `Kcb`
    drops to `dormant_kcb`. Grape."""


@dataclass(frozen=True, slots=True)
class CropParameters:
    """One crop's FAO-56 dual-Kc + root-zone parameter set. Field names
    match `docs/fao56-calculations.md` section 8/9 code identifiers."""

    name: str
    phenology: Phenology

    # --- Dual crop coefficient (section 8) ---
    kcb_ini: float
    kcb_mid: float
    kcb_end: float
    kcb_local_adjustment: float
    """Multiplicative correction applied to `kcb_mid`/`kcb_end` in `kcb_at`,
    on top of the raw FAO-56 table value. 1.0 = no adjustment. See each
    crop's docstring for why a value != 1.0 is used."""

    # --- Season timing (day-of-year, Northern Hemisphere, Manisa climate) ---
    season_start_doy: int
    """Day of year the `initial` stage begins (bud break for grape; the
    reference doc for the growing-season framing, needed even for the
    evergreen olive so the Kc curve has *a* phase reference)."""
    stage_length_init_days: int
    stage_length_dev_days: int
    stage_length_mid_days: int
    stage_length_late_days: int
    dormant_kcb: float = 0.0
    """Only used when `phenology == DECIDUOUS`."""

    # --- Root zone (section 9.1) ---
    root_depth_min_m: float = 0.0
    root_depth_max_m: float = 0.0
    depletion_fraction_p: float = 0.5
    """FAO-56 Table 22 `p` — fraction of TAW depletable with no stress."""

    # --- Canopy (section 8.2's `few`/`Kc_max` inputs) ---
    plant_height_m: float = 1.0
    ground_cover_fc: float = 0.4
    """Fraction of ground covered by canopy at mid-season. FAO-56 Table 12's
    row label for olive states this directly (40-60%); for grape it is
    literature-typical, not FAO-sourced — see module docstring."""

    def season_length_days(self) -> int:
        return (
            self.stage_length_init_days
            + self.stage_length_dev_days
            + self.stage_length_mid_days
            + self.stage_length_late_days
        )

    def root_depth_m(self, days_since_season_start: int) -> float:
        """Root depth grows linearly from `root_depth_min_m` to
        `root_depth_max_m` over the initial+development stages, per FAO-56's
        general treatment of Zr as increasing through crop development, then
        holds at the max for mid+late. For an established perennial (both
        crops here), root depth is treated as already at maximum year-round
        — this function exists for completeness/future annual-crop reuse but
        both Manisa presets below are called with a pre-grown orchard/
        vineyard in mind, so callers should generally just use
        `root_depth_max_m` directly rather than this ramp.
        """
        growth_days = self.stage_length_init_days + self.stage_length_dev_days
        if growth_days <= 0 or days_since_season_start >= growth_days:
            return self.root_depth_max_m
        if days_since_season_start <= 0:
            return self.root_depth_min_m
        frac = days_since_season_start / growth_days
        return self.root_depth_min_m + frac * (self.root_depth_max_m - self.root_depth_min_m)

    def kcb_at(self, day_of_year: int, *, days_in_year: int = 365) -> float:
        """Basal crop coefficient for a given day of year, per FAO-56's
        4-stage curve (flat `ini`, linear ramp through `dev`, flat `mid`,
        linear decline through `late`), extended outside that window per
        `phenology` (see class docstring) since neither crop is an annual
        field crop with a single bounded season.

        `kcb_local_adjustment` is applied to `kcb_mid`/`kcb_end` only (not
        `kcb_ini`) — the Mediterranean over-estimate finding this factor
        corrects for is specifically about mid/late-season transpiration
        under measured stomatal/canopy conditions, not the low-activity
        initial stage.
        """
        days_since_start = (day_of_year - self.season_start_doy) % days_in_year
        s_init = self.stage_length_init_days
        s_dev = s_init + self.stage_length_dev_days
        s_mid = s_dev + self.stage_length_mid_days
        s_late = s_mid + self.stage_length_late_days

        kcb_mid_adj = self.kcb_mid * self.kcb_local_adjustment
        kcb_end_adj = self.kcb_end * self.kcb_local_adjustment

        if days_since_start < s_init:
            return self.kcb_ini
        if days_since_start < s_dev:
            frac = (days_since_start - s_init) / max(self.stage_length_dev_days, 1)
            return self.kcb_ini + frac * (kcb_mid_adj - self.kcb_ini)
        if days_since_start < s_mid:
            return kcb_mid_adj
        if days_since_start < s_late:
            frac = (days_since_start - s_mid) / max(self.stage_length_late_days, 1)
            return kcb_mid_adj + frac * (kcb_end_adj - kcb_mid_adj)

        # Outside the defined season window.
        if self.phenology is Phenology.EVERGREEN:
            return kcb_end_adj
        return self.dormant_kcb

    def ground_cover_at(self, day_of_year: int, *, days_in_year: int = 365) -> float:
        """`fc` tracking the same seasonal curve as `kcb_at`, scaled so it
        reaches `ground_cover_fc` at mid-season and (for deciduous grape)
        falls to ~0 when dormant/leafless. Used for `few` in the Ke
        calculation (`docs/fao56-calculations.md` section 8.2). A cruder
        proxy than real S2-derived fCover — `docs/modules.md` names S2
        fCover as the eventual "hard dependency for the vegetation
        correction"; this is the rule-based-benchmark stand-in until that
        pipeline exists (`packages/etl/src/agritwin_etl/sources/sentinel2.py`
        is still a stub).
        """
        kcb_now = self.kcb_at(day_of_year, days_in_year=days_in_year)
        kcb_mid_adj = self.kcb_mid * self.kcb_local_adjustment
        if self.phenology is Phenology.EVERGREEN:
            # Never leafless; floor at a fraction of peak cover.
            baseline = 0.7 * self.ground_cover_fc
            span = kcb_mid_adj - self.kcb_ini
            frac = 0.0 if span <= 0 else (kcb_now - self.kcb_ini) / span
            return baseline + max(0.0, min(1.0, frac)) * (self.ground_cover_fc - baseline)
        span = kcb_mid_adj - self.dormant_kcb
        frac = 0.0 if span <= 0 else (kcb_now - self.dormant_kcb) / span
        return max(0.0, min(1.0, frac)) * self.ground_cover_fc


# --- Manisa presets ----------------------------------------------------------
#
# Season timing is constructed, not FAO-sourced (flagged low-confidence by
# the literature review backing this module): grape stage lengths follow a
# commonly-cited Mediterranean vineyard Kc-curve shape (bud break
# late March, full canopy ~June, harvest Aug-Sept for sultana, leaf fall
# November); olive uses the same fruit-set-to-oil-accumulation window
# (~May-October) that Mediterranean olive ET studies use to define a
# "mid-season" even though the tree never truly goes dormant.

OLIVE_MANISA = CropParameters(
    name="olive_manisa",
    phenology=Phenology.EVERGREEN,
    kcb_ini=0.65,
    kcb_mid=0.70,
    kcb_end=0.70,
    # A Mediterranean eddy-covariance olive-orchard study found the raw
    # FAO-56 Table 12 Kc overestimates actual ET by ~18% under Mediterranean
    # conditions (ScienceDirect S0378377407002715) — applied here as a
    # first-pass local correction (1 - 0.18 = 0.82), NOT itself a validated
    # Manisa-specific calibration. The benchmark notebook runs both the raw
    # and adjusted values side by side specifically to make this correction
    # visible rather than silently baking it in.
    kcb_local_adjustment=0.82,
    season_start_doy=121,  # ~May 1 — start of the fruit-set/oil-accumulation window
    stage_length_init_days=30,
    stage_length_dev_days=60,
    stage_length_mid_days=120,
    stage_length_late_days=60,
    root_depth_min_m=1.2,
    root_depth_max_m=1.7,  # FAO-56 Table 22, "Olives (40 to 60% ground coverage)"
    depletion_fraction_p=0.65,  # FAO-56 Table 22
    plant_height_m=4.0,  # FAO-56 Table 12 range 3-5 m, midpoint
    ground_cover_fc=0.5,  # FAO-56 Table 12 row label, 40-60% midpoint
)

GRAPE_MANISA = CropParameters(
    name="grape_sultana_manisa",
    phenology=Phenology.DECIDUOUS,
    # FAO-56 Table 12 "Grapes - Table" row (Manisa's dominant variety is
    # Sultaniye/sultana, a table-and-raisin type — NOT the wine-grape row).
    kcb_ini=0.30,
    kcb_mid=0.85,
    kcb_end=0.45,
    kcb_local_adjustment=1.0,  # no equivalent correction study found for this crop
    season_start_doy=80,  # ~March 21 — approximate bud break
    stage_length_init_days=35,
    stage_length_dev_days=60,
    stage_length_mid_days=100,
    stage_length_late_days=35,
    dormant_kcb=0.0,  # bare/dormant vine, no leaf area
    root_depth_min_m=1.0,
    root_depth_max_m=2.0,  # FAO-56 Table 22, "Grapes" (not split table/wine)
    depletion_fraction_p=0.45,  # FAO-56 Table 22
    plant_height_m=2.0,  # FAO-56 Table 12, table grapes
    ground_cover_fc=0.4,  # literature-typical for trellised sultana, not FAO-sourced
)


CROP_REGISTRY: dict[str, CropParameters] = {
    OLIVE_MANISA.name: OLIVE_MANISA,
    GRAPE_MANISA.name: GRAPE_MANISA,
}


def day_of_year(month: int, day: int, *, leap: bool = False) -> int:
    """Small helper: 1-indexed day of year from a (month, day) pair, so crop
    presets and callers can be written in calendar terms rather than raw
    integers. Not a full calendar library — deliberately minimal."""
    days_in_month = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[: month - 1]) + day


__all__ = [
    "Phenology",
    "CropParameters",
    "OLIVE_MANISA",
    "GRAPE_MANISA",
    "CROP_REGISTRY",
    "day_of_year",
]

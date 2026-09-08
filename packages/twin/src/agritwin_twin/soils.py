"""Soil hydraulic parameters — both the FAO-56 bucket's field
capacity/wilting point pair and the van Genuchten-Mualem closure from
`docs/fao56-calculations.md` section 11.2 (the Richards-equation constitutive
relations), for a representative Manisa-region soil texture.

`packages/etl/src/agritwin_etl/sources/soilgrids.py` is still a stub (no
real per-parcel texture data yet — `docs/decisions/data-access-layer.md`
names SoilGrids as the eventual source). Until that pipeline exists, this
module provides literature-typical presets by texture class, used as a
region-wide default rather than a per-parcel fit.

Sources: Manisa vineyard soil-survey literature (ResearchGate 366584164)
identifies clay loam as representative of the region's vineyard/olive soils.
Van Genuchten-Mualem parameters are the widely-reproduced Carsel & Parrish
(1988) 12-USDA-texture-class table — **recalled from the commonly-cited
secondary reproductions of that table (e.g. in HYDRUS/Rosetta
documentation), not re-verified against the primary paper (paywalled); treat
as literature-typical pending verification, same caveat as the crop
parameters in `crops.py`.**
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SoilParameters:
    """One texture class's water-retention parameters. Field names match
    `docs/fao56-calculations.md` sections 9.1 and 11.2 code identifiers.
    """

    name: str

    # --- FAO-56 bucket model (section 9.1) ---
    theta_fc: float
    """Field capacity, m3/m3."""
    theta_wp: float
    """Wilting point, m3/m3."""

    # --- Van Genuchten-Mualem (section 11.2) ---
    theta_r: float
    """Residual moisture, m3/m3."""
    theta_s: float
    """Saturated moisture (~porosity), m3/m3."""
    alpha_vg_per_m: float
    """Inverse air-entry pressure, m-1 (converted from the source table's
    cm-1 by x100 — see module docstring)."""
    n_vg: float
    """Pore-size distribution shape, dimensionless."""
    ks_vg_m_per_day: float
    """Saturated hydraulic conductivity, m/day. Distinct from the FAO-56
    water-stress `Ks` (section 9.3) — see
    `docs/fao56-calculations.md` section 11.2's explicit naming-collision
    warning; this module always spells it `ks_vg_*` for that reason."""
    l_mualem: float = 0.5
    """Pore connectivity parameter. Fixed at Mualem's original value per
    section 11.2 — not a per-texture fitted quantity in the standard
    formulation."""

    def m_vg(self) -> float:
        """`m = 1 - 1/n`, the van Genuchten closure relation used in both
        `psi_vg` and `K_vg` (section 11.2)."""
        return 1 - 1 / self.n_vg


# Carsel & Parrish (1988), clay loam and sandy clay loam rows.
CLAY_LOAM_MANISA = SoilParameters(
    name="clay_loam_manisa",
    theta_fc=0.30,  # midpoint of the 0.28-0.32 literature range
    theta_wp=0.15,  # midpoint of the 0.14-0.16 literature range
    theta_r=0.095,
    theta_s=0.41,
    alpha_vg_per_m=1.9,  # 0.019 cm-1 x 100
    n_vg=1.31,
    ks_vg_m_per_day=0.0624,  # 6.24 cm/day / 100
)

SANDY_CLAY_LOAM = SoilParameters(
    name="sandy_clay_loam",
    theta_fc=0.27,
    theta_wp=0.13,
    theta_r=0.100,
    theta_s=0.39,
    alpha_vg_per_m=5.9,  # 0.059 cm-1 x 100
    n_vg=1.48,
    ks_vg_m_per_day=0.3144,  # 31.44 cm/day / 100
)

SOIL_REGISTRY: dict[str, SoilParameters] = {
    CLAY_LOAM_MANISA.name: CLAY_LOAM_MANISA,
    SANDY_CLAY_LOAM.name: SANDY_CLAY_LOAM,
}

__all__ = ["SoilParameters", "CLAY_LOAM_MANISA", "SANDY_CLAY_LOAM", "SOIL_REGISTRY"]

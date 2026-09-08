"""`SoilModel` protocol — the contract between the digital twin and everything
downstream of it.

Per `docs/modules.md#digital-twin`: the twin "Owns: soil physics, observation
operator, parcel adaptation, daily assimilation. Does NOT own: When to
irrigate. Ever." Per `CLAUDE.md` rule 3: "Physics code and product code live
apart. Model implementations under `packages/twin/` implement the `SoilModel`
protocol. The decision engine never imports a concrete model class." This
file is written first, per `docs/modules.md`'s explicit instruction, so both
the bucket model (Phase 1/2, this package) and the future PINN (Phase 3) are
interchangeable behind it from day one — `docs/decisions/development-phases.md`:
"Written later, it becomes a refactor of everything downstream."

A `Protocol`, not an ABC: structural typing means a concrete model does not
need to import or subclass anything from this module to satisfy it — it only
needs the matching method shapes. That keeps the dependency direction
strictly one-way (bucket/PINN -> interface, never the reverse).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from agritwin_core.units import DepthMM, VolumetricMoisture


@dataclass(frozen=True, slots=True)
class DailyForcing:
    """One day's weather forcing for one zone — the twin's only input besides
    its own prior state and applied water. Field names match
    `docs/fao56-calculations.md`'s code identifiers exactly (`Tmax`, `Tmin`,
    `Rs`, ...) so a formula in that reference and the code implementing it
    stay visibly the same calculation.

    `date_utc` is a date, not a datetime — this system runs at daily
    timestep for satellite/soil (`docs/open-decisions.md`: "processing tempo
    is daily for satellite/soil, hourly only for weather forcing"); any
    hourly-to-daily aggregation happens before this struct is built, not
    inside the model.
    """

    date_utc: datetime
    tmax_c: float
    tmin_c: float
    rs_mj_m2_day: float
    """Incoming shortwave radiation. Prefer the weather provider's own field
    (ERA5-Land `ssrd`, Open-Meteo `shortwave_radiation`) over re-deriving it
    from sunshine hours — see `docs/fao56-calculations.md` section 2.1."""
    wind_speed_ms: float
    wind_height_m: float = 10.0
    """Height the wind speed was measured/reported at; converted to the
    FAO-56 reference height of 2 m inside `meteorology.wind_speed_2m`."""
    precip_mm: float = 0.0
    rh_max_pct: float | None = None
    rh_min_pct: float | None = None
    rh_mean_pct: float | None = None
    tdew_c: float | None = None
    """Preferred over RH when available — see
    `docs/fao56-calculations.md` section 5.2, "the more numerically stable
    path"."""


@dataclass(frozen=True, slots=True)
class SoilState:
    """The twin's daily output — exactly "state + uncertainty", per
    `docs/architecture.md` section 5 (`TWIN->>DEC: state + uncertainty`).
    Nothing here says whether to irrigate; that is the decision engine's job
    from this state alone.
    """

    valid_at: datetime
    theta: VolumetricMoisture
    """Root-zone-average volumetric soil moisture, m3/m3 — CLAUDE.md rule 5."""
    theta_std: float | None
    """Ensemble/analytic uncertainty in `theta`, m3/m3. `None` at
    degradation levels L2/L3 (bucket model fallback, `docs/architecture.md`
    section 8) — the bucket is a deterministic single-reservoir model with
    no ensemble, so it reports a point estimate and lets the decision engine
    treat missing uncertainty as "not normal confidence" rather than
    fabricating a number. The PINN (Phase 3, EnKF ensemble) is expected to
    always populate this."""
    dr_mm: DepthMM
    """Root zone depletion (`docs/fao56-calculations.md` section 9.2) — the
    same information as `theta` in the bucket model's native unit, kept
    alongside it because `Dr` is what the water-balance recurrence actually
    updates day to day; `theta` is derived from it via section 9.2's
    conversion formula."""
    ks_stress: float
    """Water stress coefficient, section 9.3, in [0, 1]. 1 = no stress."""
    raw_mm: DepthMM
    """Readily available water (`docs/fao56-calculations.md` section 9.1) —
    the depletion level at which `ks_stress` starts falling below 1. Reported
    here, not just internally, so `packages/decision/` can turn a bare `Dr`
    number into an irrigation trigger ("depleted past RAW") without itself
    knowing any crop or soil parameter — it reads the threshold the twin
    already computed, per `CLAUDE.md` rule 3 (decision engine stays
    soil-physics-free)."""
    taw_mm: DepthMM
    """Total available water, section 9.1 — the bucket's full capacity
    (`Dr = 0` is full, `Dr = taw_mm` is permanent wilting point). Reported
    alongside `raw_mm` for the same reason: it's the other end of the range
    a refill target is computed against."""
    confidence: str
    """`"normal"` or `"low"` — feeds `docs/architecture.md` section 4's
    recipe `confidence` field directly. The bucket model reports `"low"`
    when `theta` has been extrapolated for more than a configurable number
    of days without a fresh forcing/applied-water update (a crude proxy for
    "L1 stale observation" until the PINN/EnKF's real residual-based
    detection, `docs/architecture.md` section 9, exists)."""


@runtime_checkable
class SoilModel(Protocol):
    """Any soil model — bucket (this package, Phase 1/2 and the permanent
    L2/L3 fallback) or PINN (Phase 3) — implements exactly this shape. The
    decision engine (`packages/decision/`) depends on this protocol only.
    """

    def step(self, forcing: DailyForcing, applied_water_mm: DepthMM) -> SoilState:
        """Advance the model by one day given today's weather forcing and
        today's applied irrigation depth (zone-average, no `fw` applied —
        `IRRIGATION_LOG.measured_depth_mm`, `docs/schemas.md`). Returns the
        new `SoilState`. Mutates the model's internal state; `state()`
        reflects the same value immediately after.
        """
        ...

    def state(self) -> SoilState:
        """The current `SoilState` without advancing the model — e.g. for
        reporting after the most recent `step()`, or before the first one
        (initial condition)."""
        ...

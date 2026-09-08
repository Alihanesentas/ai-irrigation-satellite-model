"""Pydantic models for the core records defined in docs/schemas.md.

Field names, types, and nullability here MUST match docs/schemas.md exactly.
docs/schemas.md is the frozen source of truth (a Gate 1 deliverable — additive
changes only after freeze); this file is its typed mirror for Python code. If
they diverge, docs/schemas.md wins and this file is out of date.

Four design rules apply to every model below (see docs/schemas.md "Design rules"):

1. Store raw, derive later — e.g. IrrigationLog keeps meter_pulses and the
   k-factor in force; measured_volume_l is derived and recomputable, not the
   source of truth.
2. Log records fact, not interpretation — nothing here computes or assumes a
   soil model. `fw` (wetted fraction) lives only in ParcelAdaptation, fitted by
   the twin; IrrigationLog never applies it.
3. Every device-written record carries firmware_version.
4. Additive evolution only — never repurpose a field, never change its unit.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agritwin_core.units import (
    PydanticAreaM2,
    PydanticDepthMM,
    PydanticVolumeL,
    require_utc,
)


class IrrigationMethod(str, Enum):
    """ZONE.irrigation_method — a cohort variable, not decoration. Determines
    self-calibration feedback loop strength; see
    docs/decisions/applied-water-measurement.md."""

    SPRINKLER = "sprinkler"
    FLOOD = "flood"
    SURFACE_DRIP = "surface_drip"
    SUBSURFACE_DRIP = "subsurface_drip"


class TerminationReason(str, Enum):
    """IRRIGATION_LOG.termination_reason. Anything other than the first two
    values is a diagnosis-layer input, not a normal completion."""

    DURATION_REACHED = "duration_reached"
    TARGET_MM_REACHED = "target_mm_reached"
    RECIPE_EXPIRED = "recipe_expired"
    PRESSURE_FAULT = "pressure_fault"
    FLOW_FAULT = "flow_fault"
    OPERATOR_ABORT = "operator_abort"
    POWER_FAULT = "power_fault"
    UNKNOWN = "unknown"


class DataQuality(str, Enum):
    """IRRIGATION_LOG.data_quality. `METER_ABSENT` and `METER_SUSPECT` must be
    treated by the twin as high-uncertainty inputs, never as measurements."""

    OK = "ok"
    METER_ABSENT = "meter_absent"
    METER_SUSPECT = "meter_suspect"
    CLOCK_UNCERTAIN = "clock_uncertain"


class CommsTech(str, Enum):
    """TELEMETRY.comms_tech."""

    GSM = "gsm"
    NBIOT = "nbiot"
    LORAWAN = "lorawan"


class AdaptationConfidence(str, Enum):
    """PARCEL_ADAPTATION.confidence."""

    NORMAL = "normal"
    LOW = "low"


class Zone(BaseModel):
    """ZONE (additions) — docs/schemas.md."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    zone_id: str = Field(description="Stable across seasons")
    parcel_id: str
    area_m2: PydanticAreaM2 = Field(
        description="Required — the denominator for volume-to-depth conversion"
    )
    irrigation_method: IrrigationMethod
    nominal_flow_l_min: float = Field(
        description="Design flow; used only for plausibility checks, never as a measurement"
    )
    meter_serial: str | None = None
    meter_k_factor_l_per_pulse: float = Field(
        description="Current value; historical values live in the log"
    )


class IrrigationLog(BaseModel):
    """IRRIGATION_LOG — written by the edge node, consumed by the twin. One row
    per executed event. Idempotent on log_id: devices retry uploads after
    connectivity loss."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    log_id: uuid.UUID = Field(description="Device-generated, idempotent on re-upload")
    device_id: str
    zone_id: str
    recipe_id: str
    event_index: int = Field(description="Position within the recipe")
    firmware_version: str
    commanded_start_utc: datetime = Field(description="From the recipe")
    actual_start_utc: datetime = Field(
        description="Device clock, skew-corrected server-side"
    )
    commanded_duration_s: int
    actual_duration_s: int
    commanded_target_mm: PydanticDepthMM = Field(description="Intent only")
    meter_pulses: int = Field(description="Raw count. Never derived.")
    meter_k_factor_l_per_pulse: float = Field(
        description="Value in force at execution time"
    )
    measured_volume_l: PydanticVolumeL = Field(description="Derived; stored for convenience, recomputable")
    measured_depth_mm: PydanticDepthMM = Field(
        description="volume_l / area_m2. Zone-average. No fw applied."
    )
    flow_rate_mean_l_min: float = Field(description="Blockage and leak signal")
    flow_rate_p10_l_min: float = Field(description="Within-event variability")
    flow_rate_p90_l_min: float
    pressure_ok: bool = Field(description="From the pressure switch")
    pressure_fault_count: int = Field(description="Transient drops during the event")
    termination_reason: TerminationReason
    data_quality: DataQuality

    @field_validator("commanded_start_utc", "actual_start_utc")
    @classmethod
    def _must_be_utc(cls, v: datetime) -> datetime:
        return require_utc(v)


class Telemetry(BaseModel):
    """TELEMETRY — device health, separate from irrigation records. Written on
    each poll. The server returns its own time in every poll response; this is
    the clock discipline mechanism (devices have no NTP)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    device_id: str
    ts_utc: datetime = Field(description="Server receipt time")
    device_ts_utc: datetime = Field(description="Device clock at send")
    clock_skew_s: int = Field(description="Derived; drives the clock-drift alarm")
    firmware_version: str
    state: str = Field(description="From the edge state machine")
    battery_mv: int
    solar_mv: int | None = None
    rssi_dbm: int
    comms_tech: CommsTech
    uptime_s: int
    last_recipe_id: str | None = None
    recipe_valid_until: datetime = Field(
        description="Lets the server see an impending expiry"
    )
    fault_flags: int = Field(description="Bitfield")
    pending_log_count: int = Field(description="Unuploaded irrigation logs")

    @field_validator("ts_utc", "device_ts_utc", "recipe_valid_until")
    @classmethod
    def _must_be_utc(cls, v: datetime) -> datetime:
        return require_utc(v)


class ParcelAdaptation(BaseModel):
    """PARCEL_ADAPTATION (additions) — the Layer 1 fit. This is data, not code,
    which is what makes version management tractable."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    parcel_id: str
    z_latent: list[float] = Field(description="4-8 dimensions")
    ks_mult: float
    theta_s_offset: float
    rooting_depth_m: float
    wcm_a: float
    wcm_b: float
    fw: float = Field(description="Wetted fraction — fitted, not assumed")
    cohort_key: str = Field(description="Texture class x climate zone x irrigation method")
    fit_at: datetime
    backbone_version: str
    residual_mean: float = Field(description="Drives anomalous parcel detection")
    residual_std: float
    confidence: AdaptationConfidence

    @field_validator("fit_at")
    @classmethod
    def _must_be_utc(cls, v: datetime) -> datetime:
        return require_utc(v)

    @field_validator("z_latent")
    @classmethod
    def _latent_dims(cls, v: list[float]) -> list[float]:
        if not (4 <= len(v) <= 8):
            raise ValueError(f"z_latent must be 4-8 dimensions, got {len(v)}")
        return v


class Parcel(BaseModel):
    """PARCEL — docs/architecture.md#3-core-data-model: "geometry (PostGIS),
    crop, irrigation method, planting date, cohort key."

    `cohort_key` is intentionally nullable: docs/architecture.md#12
    ("Unresolved slots") lists it as blocked on the still-open cohort
    granularity and target cropping pattern decisions
    (docs/open-decisions.md). Do not derive it here — set null until those
    close.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    parcel_id: str
    farm_id: str
    geometry_wkt: str = Field(description="Parcel boundary, WKT polygon")
    crop: str
    planting_date: date | None = None
    cohort_key: str | None = Field(
        default=None,
        description="Texture class x climate zone x irrigation method. Null "
        "until cohort granularity and target cropping pattern are decided.",
    )
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def _must_be_utc(cls, v: datetime) -> datetime:
        return require_utc(v)


class DeviceStatus(str, Enum):
    """DEVICE.status — an edge node's lifecycle. `provisioned` means an
    api_key exists but the device has never successfully polled; `active`
    means it has. `suspended` blocks recipe issuance (safe default is
    closed, CLAUDE.md rule 6) without deleting history."""

    PROVISIONED = "provisioned"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Device(BaseModel):
    """DEVICE — docs/architecture.md#11 ("Device to backend: per-device
    credential, TLS, signed recipes verified on device").

    Only the hash of the per-device API key is ever persisted; the raw key
    is returned once, at provisioning, and cannot be recovered afterward —
    see agritwin_core.device_auth.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    device_id: str
    parcel_id: str
    api_key_hash: str = Field(description="SHA-256 hex digest of the raw API key. Never the raw key.")
    status: DeviceStatus
    firmware_version: str | None = None
    provisioned_at: datetime
    last_seen_at: datetime | None = Field(
        default=None, description="Server receipt time of the most recent successful poll"
    )

    @field_validator("provisioned_at", "last_seen_at")
    @classmethod
    def _must_be_utc(cls, v: datetime | None) -> datetime | None:
        return v if v is None else require_utc(v)


class RecipeConfidence(str, Enum):
    """RECIPE.confidence. `low` means the twin flagged an anomalous
    residual; the decision engine already produced a conservative plan —
    the device does not reinterpret it, the value only surfaces to the
    farmer. See docs/architecture.md#4."""

    NORMAL = "normal"
    LOW = "low"


class FallbackPolicy(str, Enum):
    """RECIPE.fallback_policy — applied once `valid_until` passes. Always
    `no_irrigation` unless a deliberate, documented exception exists
    (docs/architecture.md#4); no other value is defined in v1."""

    NO_IRRIGATION = "no_irrigation"


class RecipeEvent(BaseModel):
    """One scheduled irrigation event within a RECIPE zone —
    docs/architecture.md#4.

    `duration_s` is what the device executes; `target_mm` is intent only,
    carried so the device can abort early once the flow meter reaches it
    (IrrigationLog.termination_reason == target_mm_reached) and so telemetry
    can report the gap. The device never computes duration itself.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    start_utc: datetime
    duration_s: int
    target_mm: PydanticDepthMM = Field(description="Intent only — see class docstring")
    priority: int

    @field_validator("start_utc")
    @classmethod
    def _must_be_utc(cls, v: datetime) -> datetime:
        return require_utc(v)


class RecipeZone(BaseModel):
    """One zone's event list within a RECIPE — docs/architecture.md#4."""

    zone_id: str
    events: list[RecipeEvent]


class RecipeConstraints(BaseModel):
    """RECIPE.constraints — docs/architecture.md#4. Cross-zone and
    plausibility limits the device must respect even if an individual event
    would not otherwise be flagged."""

    max_concurrent_zones: int
    min_pressure_kpa: float
    max_daily_mm: float


class Recipe(BaseModel):
    """RECIPE — the recipe contract, docs/architecture.md#4: "The single
    most important interface in the system: it crosses the cloud/edge
    boundary, it is executed offline, and both sides version independently.
    Treat it as a public API from day one."

    Rules (docs/architecture.md#4):
    - `valid_until` is absolute; past it the device applies
      `fallback_policy`, never repeating the last known schedule.
    - Signed with Ed25519 (agritwin_core.recipe_signing); the device
      verifies before executing and discards an unsigned or invalid recipe
      rather than executing it (CLAUDE.md rule 6).
    - Additive schema evolution only — fielded devices run old firmware for
      years.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    schema_version: str = "1.0"
    recipe_id: str
    parcel_id: str
    issued_at: datetime
    valid_from: datetime
    valid_until: datetime
    confidence: RecipeConfidence
    fallback_policy: FallbackPolicy
    zones: list[RecipeZone]
    constraints: RecipeConstraints
    signature: str | None = Field(
        default=None,
        description="'ed25519:<base64>', set by agritwin_core.recipe_signing.sign_recipe. "
        "Null only before signing; a recipe must never be transmitted unsigned.",
    )

    @field_validator("issued_at", "valid_from", "valid_until")
    @classmethod
    def _must_be_utc(cls, v: datetime) -> datetime:
        return require_utc(v)

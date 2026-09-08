"""Unit-safety wrappers.

CLAUDE.md rule 5: soil moisture is always volumetric (m3/m3), water depth is mm,
time is UTC. Local-time conversion happens only in the edge layer, with an
explicit offset.

This is a safety-critical system — a valve actuates from these numbers. A bare
`float` lets a depth in mm be added to a moisture fraction in m3/m3 and the bug
surfaces as a mis-timed irrigation, not a type error. Every quantity that
crosses a module boundary in this codebase should be one of the types below,
never a bare float or bare datetime.

Design: immutable dataclasses, one per unit family. Arithmetic is only defined
within the same unit (dimensionally safe). Cross-unit conversion (e.g. a
measured litre volume to a zone-average depth) requires an explicit function
that takes the extra input the conversion needs (e.g. `area_m2`) — there is no
implicit division hiding in an operator.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated

from pydantic import BeforeValidator, PlainSerializer


@dataclass(frozen=True, slots=True)
class VolumetricMoisture:
    """Soil moisture, m3/m3. Always in [0, 1] for physically valid states."""

    value: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 1.0):
            raise ValueError(
                f"VolumetricMoisture out of physical range [0, 1]: {self.value}"
            )

    def __add__(self, other: "VolumetricMoisture") -> "VolumetricMoisture":
        return VolumetricMoisture(self.value + other.value)

    def __sub__(self, other: "VolumetricMoisture") -> "VolumetricMoisture":
        return VolumetricMoisture(self.value - other.value)


@dataclass(frozen=True, slots=True)
class DepthMM:
    """Water depth, millimetres. Used for ET0, applied water, precipitation."""

    value: float

    def __add__(self, other: "DepthMM") -> "DepthMM":
        return DepthMM(self.value + other.value)

    def __sub__(self, other: "DepthMM") -> "DepthMM":
        return DepthMM(self.value - other.value)

    def __mul__(self, scalar: float) -> "DepthMM":
        return DepthMM(self.value * scalar)


@dataclass(frozen=True, slots=True)
class VolumeL:
    """Water volume, litres. Raw meter-derived quantity — see IRRIGATION_LOG in
    schema.py: pulses and k-factor are stored raw, volume is derived for
    convenience and must remain recomputable from them."""

    value: float

    def __add__(self, other: "VolumeL") -> "VolumeL":
        return VolumeL(self.value + other.value)


@dataclass(frozen=True, slots=True)
class AreaM2:
    """Zone or parcel area, square metres. The required denominator for any
    volume-to-depth conversion — see ZONE.area_m2 in schema.py."""

    value: float

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError(f"AreaM2 must be positive: {self.value}")


def volume_to_zone_average_depth(volume: VolumeL, area: AreaM2) -> DepthMM:
    """Zone-average depth from a metered volume: depth_mm = volume_l / area_m2.

    Matches IRRIGATION_LOG.measured_depth_mm in schema.py exactly: 1 litre over
    1 m2 is 1 mm of depth, no conversion factor needed.

    No wetted fraction is applied here. Per docs/schemas.md: "measured_depth_mm
    is zone-average... Wetted fraction is applied by the twin, never here."
    Applying `fw` at this call site would violate that boundary.
    """
    return DepthMM(volume.value / area.value)


def depth_to_volume(depth: DepthMM, area: AreaM2) -> VolumeL:
    """Inverse of `volume_to_zone_average_depth`: the volume needed to apply
    a target zone-average depth over a zone's area. `packages/decision` uses
    this to turn a planned refill depth (mm) into a volume, on the way to a
    `duration_s` via the zone's nominal flow rate — the same mm-to-litres
    relationship as the metered-volume path, just run in the other
    direction, so it belongs next to it rather than being reimplemented at
    the call site."""
    return VolumeL(depth.value * area.value)


def utc_now() -> datetime:
    """The only sanctioned way to get 'now' in this codebase. Always
    timezone-aware UTC — never naive, never local."""
    return datetime.now(timezone.utc)


def require_utc(dt: datetime) -> datetime:
    """Guard for any datetime crossing a module boundary. Raises if the
    datetime is naive or not UTC, rather than silently trusting it.

    Local-time conversion is only permitted in the edge layer (firmware/), with
    an explicit offset applied there — never implicitly here.
    """
    if dt.tzinfo is None:
        raise ValueError(f"Naive datetime not allowed, got {dt!r}. Attach UTC tzinfo.")
    if dt.utcoffset() != timezone.utc.utcoffset(None):
        raise ValueError(f"Datetime must be UTC, got offset {dt.utcoffset()} for {dt!r}")
    return dt


# --- Pydantic wire adapters -------------------------------------------------
#
# A plain `arbitrary_types_allowed` model field accepts these dataclasses in
# Python but has no defined JSON wire format. Every record in schemas.md and
# the recipe contract in architecture.md ("target_mm": 12.0) puts these
# quantities on the wire as bare numbers, unit implied by field name — so the
# JSON shape must stay a bare float even though the Python-side type stays
# unit-safe. These `Annotated` aliases are what makes both true at once: use
# them (not the raw dataclass) as a pydantic model field's type.


def _depth_mm(v: object) -> DepthMM:
    return v if isinstance(v, DepthMM) else DepthMM(float(v))  # type: ignore[arg-type]


def _area_m2(v: object) -> AreaM2:
    return v if isinstance(v, AreaM2) else AreaM2(float(v))  # type: ignore[arg-type]


def _volume_l(v: object) -> VolumeL:
    return v if isinstance(v, VolumeL) else VolumeL(float(v))  # type: ignore[arg-type]


def _volumetric_moisture(v: object) -> VolumetricMoisture:
    return v if isinstance(v, VolumetricMoisture) else VolumetricMoisture(float(v))  # type: ignore[arg-type]


PydanticDepthMM = Annotated[
    DepthMM, BeforeValidator(_depth_mm), PlainSerializer(lambda d: d.value, return_type=float)
]
PydanticAreaM2 = Annotated[
    AreaM2, BeforeValidator(_area_m2), PlainSerializer(lambda d: d.value, return_type=float)
]
PydanticVolumeL = Annotated[
    VolumeL, BeforeValidator(_volume_l), PlainSerializer(lambda d: d.value, return_type=float)
]
PydanticVolumetricMoisture = Annotated[
    VolumetricMoisture,
    BeforeValidator(_volumetric_moisture),
    PlainSerializer(lambda d: d.value, return_type=float),
]

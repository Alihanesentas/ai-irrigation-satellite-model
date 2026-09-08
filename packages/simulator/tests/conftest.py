"""Shared fixtures for the whole simulator test suite (unit tests +
conformance suite). Everything here is wired through the *public* interface
of `agritwin_simulator` and `agritwin_core` — no simulator internals.
"""

from __future__ import annotations

from datetime import timedelta

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from agritwin_core.recipe_signing import generate_keypair
from agritwin_core.schema import (
    FallbackPolicy,
    Recipe,
    RecipeConfidence,
    RecipeConstraints,
    RecipeEvent,
    RecipeZone,
)
from agritwin_core.units import utc_now
from agritwin_simulator import DeviceSimulator, FakeBackend, VirtualClock, ZoneRuntimeConfig

DEVICE_ID = "dev-0001"
PARCEL_ID = "prc-0001"
API_KEY = "test-api-key-0001"
ZONE_ID = "z1"

DEFAULT_ZONE_CONFIGS = {
    ZONE_ID: ZoneRuntimeConfig(
        area_m2=500.0,
        meter_k_factor_l_per_pulse=0.5,
        nominal_flow_l_min=60.0,
    ),
}


@pytest.fixture()
def keypair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    return generate_keypair()


@pytest.fixture()
def backend(keypair: tuple[Ed25519PrivateKey, Ed25519PublicKey]) -> FakeBackend:
    private_key, _ = keypair
    fb = FakeBackend(private_key)
    fb.register_device(DEVICE_ID, PARCEL_ID, API_KEY)
    return fb


@pytest.fixture()
def clock() -> VirtualClock:
    return VirtualClock(start=utc_now())


@pytest.fixture()
def make_device(backend: FakeBackend, keypair, clock: VirtualClock):
    """Factory for a DeviceSimulator wired to the shared FakeBackend over an
    in-memory httpx.MockTransport. Callers can override zone_configs,
    wake_interval_s, rng_seed, etc.
    """
    _, public_key = keypair

    def _make(**overrides: object) -> DeviceSimulator:
        kwargs: dict[object, object] = dict(
            device_id=DEVICE_ID,
            parcel_id=PARCEL_ID,
            api_key=API_KEY,
            backend_public_key=public_key,
            transport=httpx.MockTransport(backend.handle_request),
            zone_configs=DEFAULT_ZONE_CONFIGS,
            clock=clock,
            wake_interval_s=24 * 3600,
            rng_seed=1234,
        )
        kwargs.update(overrides)
        return DeviceSimulator(**kwargs)  # type: ignore[arg-type]

    return _make


def _make_recipe(
    *,
    now,
    recipe_id: str = "r-0001",
    valid_for: timedelta = timedelta(hours=24),
    event_offset: timedelta = timedelta(minutes=5),
    duration_s: int = 1800,
    target_mm: float = 8.0,
    zone_id: str = ZONE_ID,
    confidence: RecipeConfidence = RecipeConfidence.NORMAL,
    extra_events: list[RecipeEvent] | None = None,
) -> Recipe:
    """Build an unsigned Recipe matching docs/architecture.md#4's shape.
    Callers sign it via `backend.put_recipe(...)` (which uses the real
    Ed25519 signer) before serving it."""
    events = [
        RecipeEvent(
            start_utc=now + event_offset,
            duration_s=duration_s,
            target_mm=target_mm,
            priority=1,
        )
    ]
    if extra_events:
        events.extend(extra_events)
    return Recipe(
        recipe_id=recipe_id,
        parcel_id=PARCEL_ID,
        issued_at=now,
        valid_from=now,
        valid_until=now + valid_for,
        confidence=confidence,
        fallback_policy=FallbackPolicy.NO_IRRIGATION,
        zones=[RecipeZone(zone_id=zone_id, events=events)],
        constraints=RecipeConstraints(max_concurrent_zones=1, min_pressure_kpa=150, max_daily_mm=20),
    )


@pytest.fixture()
def make_recipe():
    """Fixture wrapper around `_make_recipe` so conformance tests in
    `tests/conformance/` (a separate import root from this conftest) can
    consume it without importing simulator/test internals directly."""
    return _make_recipe


@pytest.fixture()
def zone_id() -> str:
    return ZONE_ID

"""Gate 1 conformance: an unsigned/tampered recipe must be discarded and the
device must never reach Armed. CLAUDE.md rule 6 — safe default is closed.
"""

from __future__ import annotations

from agritwin_core.schema import RecipeConfidence
from agritwin_simulator import DeviceState


def test_tampered_recipe_is_discarded_never_armed(backend, clock, make_device, make_recipe):
    recipe = make_recipe(now=clock.now())
    backend.put_recipe(recipe.parcel_id, recipe)
    # Mutate a field on the already-signed recipe without re-signing —
    # signature no longer covers the payload.
    backend.tamper_current_recipe(recipe.parcel_id, confidence=RecipeConfidence.LOW)

    device = make_device()
    device.wake_and_sync()

    assert device.state == DeviceState.SLEEP
    assert device.current_recipe is None
    assert len(backend.irrigation_logs) == 0


def test_unsigned_recipe_is_discarded_never_armed(backend, clock, make_device, make_recipe):
    recipe = make_recipe(now=clock.now())
    signed = backend.put_recipe(recipe.parcel_id, recipe)
    # Strip the signature entirely and re-store — simulates a malformed /
    # unsigned payload reaching the device.
    unsigned = signed.model_copy(update={"signature": None})
    backend.store_raw_recipe(recipe.parcel_id, unsigned)

    device = make_device()
    device.wake_and_sync()

    assert device.state == DeviceState.SLEEP
    assert device.current_recipe is None


def test_wrong_signing_key_is_discarded_never_armed(backend, clock, make_device, make_recipe):
    from agritwin_core.recipe_signing import generate_keypair, sign_recipe

    recipe = make_recipe(now=clock.now())
    other_private, _ = generate_keypair()
    wrongly_signed = sign_recipe(recipe, other_private)
    backend.store_raw_recipe(recipe.parcel_id, wrongly_signed)  # bypass the backend's own signer

    device = make_device()
    device.wake_and_sync()

    assert device.state == DeviceState.SLEEP
    assert device.current_recipe is None

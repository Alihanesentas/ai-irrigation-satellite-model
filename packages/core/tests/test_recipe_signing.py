from datetime import datetime, timezone

from agritwin_core.recipe_signing import (
    generate_keypair,
    private_key_from_pem,
    private_key_to_pem,
    public_key_from_pem,
    public_key_to_pem,
    sign_recipe,
    verify_recipe,
)
from agritwin_core.schema import (
    FallbackPolicy,
    Recipe,
    RecipeConfidence,
    RecipeConstraints,
    RecipeEvent,
    RecipeZone,
)


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def _sample_recipe() -> Recipe:
    return Recipe(
        recipe_id="01J9X2",
        parcel_id="prc_8821",
        issued_at=_utc(2026, 8, 18, 2, 10),
        valid_from=_utc(2026, 8, 18, 0, 0),
        valid_until=_utc(2026, 8, 20, 0, 0),
        confidence=RecipeConfidence.NORMAL,
        fallback_policy=FallbackPolicy.NO_IRRIGATION,
        zones=[
            RecipeZone(
                zone_id="z1",
                events=[
                    RecipeEvent(
                        start_utc=_utc(2026, 8, 18, 2, 30),
                        duration_s=5400,
                        target_mm=12.0,
                        priority=1,
                    )
                ],
            )
        ],
        constraints=RecipeConstraints(
            max_concurrent_zones=1, min_pressure_kpa=150, max_daily_mm=20
        ),
    )


def test_sign_then_verify_succeeds():
    private_key, public_key = generate_keypair()
    signed = sign_recipe(_sample_recipe(), private_key)

    assert signed.signature is not None
    assert signed.signature.startswith("ed25519:")
    assert verify_recipe(signed, public_key) is True


def test_unsigned_recipe_fails_verification():
    _, public_key = generate_keypair()
    assert verify_recipe(_sample_recipe(), public_key) is False


def test_tampered_field_after_signing_fails_verification():
    private_key, public_key = generate_keypair()
    signed = sign_recipe(_sample_recipe(), private_key)

    tampered = signed.model_copy(update={"valid_until": _utc(2099, 1, 1)})
    assert verify_recipe(tampered, public_key) is False


def test_wrong_key_fails_verification():
    private_key, _ = generate_keypair()
    _, other_public_key = generate_keypair()
    signed = sign_recipe(_sample_recipe(), private_key)

    assert verify_recipe(signed, other_public_key) is False


def test_pem_round_trip_preserves_signing_behaviour():
    private_key, public_key = generate_keypair()
    restored_private = private_key_from_pem(private_key_to_pem(private_key))
    restored_public = public_key_from_pem(public_key_to_pem(public_key))

    signed = sign_recipe(_sample_recipe(), restored_private)
    assert verify_recipe(signed, restored_public) is True

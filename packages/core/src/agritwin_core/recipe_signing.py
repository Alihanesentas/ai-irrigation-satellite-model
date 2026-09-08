"""Ed25519 signing and verification for the recipe contract.

See docs/architecture.md#4 ("The recipe contract") and #11 ("Security and
data boundaries"): the backend signs every recipe; the edge node verifies
before executing and discards an unsigned or invalid one rather than
executing it — CLAUDE.md rule 6, safe default is closed.

The backend holds the Ed25519 private key; every provisioned device is
flashed with the corresponding public key. A leaked per-device API key
(agritwin_core.device_auth) therefore cannot be used to forge a recipe — it
only authenticates that device's own telemetry and log uploads.
"""

from __future__ import annotations

import base64
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from agritwin_core.schema import Recipe

SIGNATURE_ALGORITHM = "ed25519"
_PREFIX = f"{SIGNATURE_ALGORITHM}:"


def canonical_payload(recipe: Recipe) -> bytes:
    """The exact bytes a signature covers: the recipe's JSON with
    `signature` excluded, keys sorted. Signer and verifier must hash
    identical bytes regardless of field insertion order — this is that
    single canonicalisation point.
    """
    data = recipe.model_dump(mode="json", exclude={"signature"})
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_recipe(recipe: Recipe, private_key: Ed25519PrivateKey) -> Recipe:
    """Return a copy of `recipe` with `signature` populated. `recipe` itself
    is not mutated (Recipe fields are otherwise immutable-by-convention
    once issued)."""
    raw_signature = private_key.sign(canonical_payload(recipe))
    encoded = _PREFIX + base64.b64encode(raw_signature).decode("ascii")
    return recipe.model_copy(update={"signature": encoded})


def verify_recipe(recipe: Recipe, public_key: Ed25519PublicKey) -> bool:
    """True only if `recipe.signature` is well-formed and verifies against
    `public_key` for this exact payload. Any failure — missing prefix, bad
    base64, wrong key, tampered field — returns False rather than raising:
    callers on the edge must be able to treat this as a plain discard
    decision, not exception handling on a safety-critical path.
    """
    if not recipe.signature or not recipe.signature.startswith(_PREFIX):
        return False
    try:
        raw_signature = base64.b64decode(recipe.signature[len(_PREFIX) :], validate=True)
    except (ValueError, TypeError):
        return False
    try:
        public_key.verify(raw_signature, canonical_payload(recipe))
    except InvalidSignature:
        return False
    return True


def generate_keypair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """New backend signing keypair. Call once per environment and persist
    the private key (e.g. via Settings, packages/etl-style) — regenerating
    it invalidates every device's embedded public key."""
    private_key = Ed25519PrivateKey.generate()
    return private_key, private_key.public_key()


def private_key_to_pem(private_key: Ed25519PrivateKey) -> str:
    return private_key.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
    ).decode("ascii")


def private_key_from_pem(pem: str) -> Ed25519PrivateKey:
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    key = load_pem_private_key(pem.encode("ascii"), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("PEM does not contain an Ed25519 private key")
    return key


def public_key_to_pem(public_key: Ed25519PublicKey) -> str:
    return public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode(
        "ascii"
    )


def public_key_from_pem(pem: str) -> Ed25519PublicKey:
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    key = load_pem_public_key(pem.encode("ascii"))
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("PEM does not contain an Ed25519 public key")
    return key

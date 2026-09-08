"""Per-device API key generation and hashing.

docs/architecture.md#11: "Device to backend: per-device credential, TLS,
signed recipes verified on device." This is the credential half of that
boundary — recipe integrity itself is Ed25519, see recipe_signing.py.

Single abstraction point, same rationale as agritwin_etl.config.Settings:
every caller (packages/api at provisioning and at request auth) goes through
these two functions rather than rolling its own token generation or hashing,
so the scheme can change in one place.
"""

from __future__ import annotations

import hashlib
import secrets

_API_KEY_NBYTES = 32  # 256 bits


def generate_api_key() -> str:
    """A new, URL-safe, per-device secret. Shown to the operator exactly
    once at provisioning — only its hash is ever persisted (Device.api_key_hash)."""
    return secrets.token_urlsafe(_API_KEY_NBYTES)


def hash_api_key(raw_key: str) -> str:
    """SHA-256 hex digest of `raw_key`. Deterministic and unsalted by
    design: this is a high-entropy generated secret (256 bits), not a
    user-chosen password, so dictionary/rainbow-table attacks are not the
    threat model — a fast, comparable digest is what request-auth needs on
    every poll."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def verify_api_key(raw_key: str, expected_hash: str) -> bool:
    """Constant-time comparison against a stored hash."""
    return secrets.compare_digest(hash_api_key(raw_key), expected_hash)

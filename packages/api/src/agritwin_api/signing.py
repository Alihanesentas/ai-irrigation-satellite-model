"""Backend Ed25519 signing keypair — load-or-generate, single access point.

Every provisioned device is (eventually) flashed with the public half of
this keypair; the backend holds the private half and signs every recipe
with it (`agritwin_core.recipe_signing.sign_recipe`). See
docs/architecture.md#4 and #11.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from agritwin_core.recipe_signing import (
    generate_keypair,
    private_key_from_pem,
    private_key_to_pem,
)
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from agritwin_api.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_signing_keys() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """The process-wide (private, public) Ed25519 keypair. Loaded from
    `Settings.signing_private_key_path` if it exists; generated and
    persisted there otherwise."""
    settings = get_settings()
    path = Path(settings.signing_private_key_path)
    if path.exists():
        private_key = private_key_from_pem(path.read_text(encoding="utf-8"))
    else:
        private_key, _ = generate_keypair()
        if path.parent != Path(""):
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(private_key_to_pem(private_key), encoding="utf-8")
        logger.warning(
            "No signing key found at %s; generated a new Ed25519 keypair. "
            "Any previously provisioned device's embedded public key is "
            "now stale.",
            path,
        )
    return private_key, private_key.public_key()

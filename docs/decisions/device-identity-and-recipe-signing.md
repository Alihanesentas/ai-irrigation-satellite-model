# Device identity and recipe signing

**Status:** Accepted

## Context

`delivery-plan.md` lists two items that must close before Phase 1 (Gate 1) ends: the device
identity/credential model, and whether `target_mm` early-abort is in scope for v1. Both were
already implicit in `architecture.md` (`#4` "The recipe contract" shows a `signature:
"ed25519:..."` field and `target_mm` carried in each recipe event; `#11` "Security and data
boundaries" names "per-device credential" and "Ed25519 signature") but neither had a formal
decision record or an implementation. This record closes both, and is the basis for
`agritwin_core.recipe_signing` and `agritwin_core.device_auth`.

## Decision

**Two independent credentials, not one:**

1. **Recipe integrity — Ed25519, server-signed, device-verified.** The backend holds a single
   Ed25519 private key. Every recipe is signed before it leaves the backend
   (`recipe_signing.sign_recipe`). Every provisioned device is flashed with the corresponding
   public key and verifies before executing (`recipe_signing.verify_recipe`); an unsigned or
   invalid recipe is discarded, never executed (`CLAUDE.md` rule 6).
2. **Device authenticity — per-device API key, bearer token over TLS.** Each device is
   provisioned with a random 256-bit key (`device_auth.generate_api_key`); only its SHA-256
   hash is persisted server-side (`device_auth.hash_api_key`). The raw key is shown once, at
   provisioning, and authenticates that device's poll, telemetry, and log-upload requests.

**`target_mm` early-abort is in scope for v1.** A device that reaches the commanded volume
(via `meter_pulses` x `meter_k_factor_l_per_pulse`) before `duration_s` elapses may stop the
event early and record `TerminationReason.TARGET_MM_REACHED`. `schema.py` already carried this
enum value; this record makes the behaviour explicit rather than merely representable.

## Rationale

**Why two credentials instead of one shared secret.** A single HMAC secret per device would
make that device's own key sufficient to forge a recipe for itself. Recipe integrity is the
higher-stakes boundary — a forged recipe opens a valve; a forged telemetry/log upload does
not. Splitting them means a leaked device API key only lets an attacker impersonate that one
device's *reports*, never fabricate an executable recipe. This follows directly from `CLAUDE.md`
rule 6 (safe default is closed) applied to the credential design itself, not just the runtime
state machine.

**Why Ed25519 specifically.** Small keys and signatures (crucial for a 24-48h JSON recipe
polled over GSM/NB-IoT/LoRaWAN), fast verification on a constrained MCU, and available in both
ESP-IDF's mbedTLS and Zephyr's TinyCrypt — no new dependency class for `firmware/`. Matches
`CLAUDE.md` rule 4 (boring technology wins): this is the standard choice for
signature-verify-only embedded firmware, not a novel construction.

**Why a bearer API key rather than mTLS for device authenticity.** mTLS would require a
per-device CA-issued client certificate and certificate lifecycle management (renewal,
revocation) on top of the Ed25519 recipe-signing keypair the system already needs. A
provisioned, hashed, rotatable bearer token over TLS gets the same practical guarantee (only
this device can authenticate as itself) with one fewer PKI to operate, consistent with
`CLAUDE.md` rule 4.

**Why `target_mm` early-abort belongs in v1.** The alternative — running full `duration_s`
regardless of measured volume — means a system that already has the metered volume in hand
each event ignores it until after the fact, over-irrigating whenever the recipe's duration
estimate ran long. `schemas.md`'s `TerminationReason.TARGET_MM_REACHED` value only makes sense
if a device is expected to reach it during normal operation, not only under fault conditions.

## Consequences

- `Device.api_key_hash` never stores a recoverable secret; a database compromise cannot be
  used to impersonate a device without also compromising the physical key material.
- The backend's Ed25519 private key is a single high-value secret — its compromise lets an
  attacker forge recipes for every device. It must be stored the same way other credentials in
  this system are (see `agritwin_etl.config.Settings`'s rationale), not hardcoded, and rotation
  requires re-flashing every device's embedded public key — expensive, so key storage/backup
  discipline matters more here than for the per-device API keys.
- The edge node's state machine (`architecture.md#7`) `Validate` state now has a concrete
  meaning: verify the Ed25519 signature over the canonical (signature-excluded, sorted-key)
  JSON payload; on failure, transition to `Sleep`, not `Armed`.
- Conformance suite (`delivery-plan.md` Phase 1) must include: valid signature accepted,
  tampered field after signing rejected, wrong/foreign key rejected, missing signature
  rejected, and a `target_mm`-reached mid-duration early stop recorded with the correct
  `termination_reason`.

## Rejected

- **Symmetric HMAC for both device auth and recipe integrity** — simplest, but a leaked
  per-device secret would let an attacker forge a valid recipe for that device, directly
  contradicting rule 6. See Rationale.
- **mTLS per device** — stronger identity guarantee, but adds a second PKI (certificate
  issuance, renewal, revocation) alongside the Ed25519 recipe-signing keypair the system
  already requires, for no additional protection on the boundary that actually actuates a
  valve. Revisit only if a concrete attack on bearer tokens over TLS is identified.
- **No early-abort (always run full `duration_s`)** — simpler device logic, but wastes the
  metered volume the applied-water-measurement decision specifically added, and contradicts
  the fail-toward-conservative spirit of rule 6 by irrigating past the commanded target
  whenever the duration estimate is loose.

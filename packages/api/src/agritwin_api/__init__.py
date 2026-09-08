"""agritwin_api — Cloud backend (packages/api).

Owns transport, identity, persistence, device registry, and telemetry
ingest. Owns NO business logic or decision-making — see
docs/modules.md#cloud-backend. Recipes are produced by the (not-yet-built)
decision engine in Phase 2; in this Gate 1 skeleton they are injected
directly via the admin API as a stand-in.
"""

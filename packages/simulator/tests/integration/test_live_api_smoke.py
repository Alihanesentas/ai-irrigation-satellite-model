"""Opt-in smoke test against a real, running `packages/api` instance.

`packages/api` is being built in parallel against the same HTTP contract
this simulator speaks (see `agritwin_simulator.client.BackendClient`). This
test is deliberately isolated from the self-contained `tests/conformance/`
suite (which uses `FakeBackend` and never needs a live server) and is
skipped by default, since `packages/api` may not exist or be running when
this suite runs.

Enable with:

    AGRITWIN_LIVE_API=1 AGRITWIN_LIVE_API_URL=http://localhost:8000 \
        uv run pytest tests/integration -q

The test only exercises the unauthenticated-failure path (401 on a bogus
device/key) so it needs no admin fixture setup on the live server — it is a
transport/reachability smoke check, not a full conformance run against real
firmware.
"""

from __future__ import annotations

import os

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("AGRITWIN_LIVE_API") != "1",
    reason="opt-in only: set AGRITWIN_LIVE_API=1 to run against a live packages/api instance",
)


def test_live_api_rejects_unknown_device() -> None:
    base_url = os.environ.get("AGRITWIN_LIVE_API_URL", "http://localhost:8000")
    with httpx.Client(base_url=base_url, timeout=5.0) as client:
        resp = client.get(
            "/devices/does-not-exist/recipe",
            headers={"Authorization": "Bearer not-a-real-key"},
        )
    assert resp.status_code in (401, 403, 404)

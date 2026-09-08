from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def isolated_app_state(tmp_path, monkeypatch):
    """Every test gets its own SQLite file, its own signing keypair, and a
    known admin key, by pointing the env-backed Settings at a temp dir and
    clearing every lru_cache that memoises process state. Without this,
    tests would share one on-disk database and keypair across the whole
    run."""
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("SIGNING_PRIVATE_KEY_PATH", str(tmp_path / "signing_key.pem"))
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")

    from agritwin_api import config, db, signing

    def _reset() -> None:
        config.get_settings.cache_clear()
        config.get_admin_api_key.cache_clear()
        signing.get_signing_keys.cache_clear()
        db.get_engine.cache_clear()
        db.reset_session_factory()

    _reset()
    yield
    _reset()


@pytest.fixture
def client() -> TestClient:
    from agritwin_api.main import app

    return TestClient(app)


ADMIN_HEADERS = {"Authorization": "Bearer test-admin-key"}

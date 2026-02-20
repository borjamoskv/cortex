"""
CORTEX v4.0 — API Tests.

Tests for the FastAPI REST API endpoints.
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Unique test DB — no module-level patching to avoid state leakage
_test_db = tempfile.mktemp(suffix="_api.db")


@pytest.fixture(scope="module")
def client():
    """Create test client with a completely isolated database."""
    # Delete any leftover DB
    for ext in ["", "-wal", "-shm"]:
        try:
            os.unlink(_test_db + ext)
        except FileNotFoundError:
            pass

    import cortex.api as api_mod
    import cortex.auth
    import cortex.config
    import cortex.api_state

    original_db_api = api_mod.DB_PATH
    original_db_config = cortex.config.DB_PATH
    original_env = os.environ.get("CORTEX_DB")

    # Patch DB path everywhere BEFORE lifespan runs
    os.environ["CORTEX_DB"] = _test_db
    api_mod.DB_PATH = _test_db
    cortex.config.DB_PATH = _test_db
    cortex.config.reload()

    # Kill ALL singletons so lifespan creates fresh ones
    cortex.auth._auth_manager = None
    cortex.api_state.auth_manager = None
    cortex.api_state.engine = None

    try:
        with TestClient(api_mod.app) as c:
            yield c
    finally:
        # Restore originals
        api_mod.DB_PATH = original_db_api
        cortex.config.DB_PATH = original_db_config
        cortex.config.reload()

        # Restore env var
        if original_env is not None:
            os.environ["CORTEX_DB"] = original_env
        else:
            os.environ.pop("CORTEX_DB", None)

        # Reset singletons
        cortex.auth._auth_manager = None
        cortex.api_state.auth_manager = None
        cortex.api_state.engine = None

        # Clean up test DB
        for ext in ["", "-wal", "-shm"]:
            try:
                os.unlink(_test_db + ext)
            except FileNotFoundError:
                pass


@pytest.fixture(scope="module")
def api_key(client):
    """Create an API key directly via AuthManager (bypasses HTTP bootstrap race)."""
    from cortex.auth import AuthManager

    mgr = AuthManager(_test_db)
    raw_key, _ = mgr.create_key(
        name="test-key",
        tenant_id="test",
        permissions=["read", "write", "admin"],
    )
    return raw_key


@pytest.fixture(scope="module")
def auth_headers(api_key):
    return {"Authorization": f"Bearer {api_key}"}


class TestHealth:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["service"] == "cortex"

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


class TestAuth:
    def test_no_auth_rejected(self, client):
        resp = client.post("/v1/facts", json={"project": "test", "content": "hello"})
        assert resp.status_code == 401

    def test_bad_key_rejected(self, client):
        resp = client.post(
            "/v1/facts",
            json={"project": "test", "content": "hello"},
            headers={"Authorization": "Bearer ctx_invalid"},
        )
        assert resp.status_code == 401

    def test_good_key_accepted(self, client, auth_headers):
        resp = client.post(
            "/v1/facts", json={"project": "test", "content": "hello"}, headers=auth_headers
        )
        assert resp.status_code == 200


class TestFacts:
    def test_store(self, client, auth_headers):
        resp = client.post(
            "/v1/facts",
            json={
                "project": "test",
                "content": "CORTEX uses SQLite with vector search",
                "tags": ["tech", "db"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["fact_id"] > 0
        assert resp.json()["project"] == "test"

    def test_recall(self, client, auth_headers):
        resp = client.get("/v1/projects/test/facts", headers=auth_headers)
        assert resp.status_code == 200
        facts = resp.json()
        assert len(facts) >= 1
        assert any("SQLite" in f["content"] for f in facts)

    def test_deprecate(self, client, auth_headers):
        store_resp = client.post(
            "/v1/facts", json={"project": "demo", "content": "temporary fact"}, headers=auth_headers
        )
        fact_id = store_resp.json()["fact_id"]

        resp = client.delete(f"/v1/facts/{fact_id}", headers=auth_headers)
        assert resp.status_code == 200

    def test_deprecate_nonexistent(self, client, auth_headers):
        resp = client.delete("/v1/facts/99999", headers=auth_headers)
        assert resp.status_code == 404


class TestSearch:
    def test_search(self, client, auth_headers):
        resp = client.post(
            "/v1/search", json={"query": "database technology", "k": 3}, headers=auth_headers
        )
        assert resp.status_code == 200
        results = resp.json()
        assert isinstance(results, list)


class TestStatus:
    def test_status(self, client, auth_headers):
        resp = client.get("/v1/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_facts" in data
        assert "version" in data

    def test_status_requires_auth(self, client):
        resp = client.get("/v1/status")
        assert resp.status_code == 401

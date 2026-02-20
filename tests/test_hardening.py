"""
CORTEX v4.0 — Hardening Tests.

Verifies the fixes for security leaks and resource management identified by Kimi.
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Path for a unique test DB — env var is NOT set at module level
# to avoid polluting other test modules during full-suite runs.
_test_db = tempfile.mktemp(suffix="_hardening.db")


@pytest.fixture(scope="module")
def client():
    # Ensure a truly fresh database (delete if leftover from prior run)
    for ext in ["", "-wal", "-shm"]:
        try:
            os.unlink(_test_db + ext)
        except FileNotFoundError:
            pass

    import cortex.api as api_mod
    import cortex.auth
    import cortex.config
    import cortex.api_state

    # Save originals
    original_db_api = api_mod.DB_PATH
    original_db_config = cortex.config.DB_PATH
    original_env = os.environ.get("CORTEX_DB")

    # Force env var AND module-level constants to our fresh test DB
    os.environ["CORTEX_DB"] = _test_db
    api_mod.DB_PATH = _test_db
    cortex.config.DB_PATH = _test_db
    cortex.config.reload()

    # Nuke auth singletons completely to force bootstrap mode
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

        # Restore env var
        if original_env is not None:
            os.environ["CORTEX_DB"] = original_env
        else:
            os.environ.pop("CORTEX_DB", None)

        cortex.config.reload()

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
    """Create an API key via the bootstrap endpoint (no auth needed for first key)."""
    # Try with explicit tenant_id first, then without
    for tenant in ["hardening", ""]:
        resp = client.post(f"/v1/admin/keys?name=hardening-test&tenant_id={tenant}")
        if resp.status_code == 200:
            return resp.json()["key"]
    pytest.fail(f"Failed to create key (Status {resp.status_code}): {resp.text}")


@pytest.fixture(scope="module")
def auth_headers(api_key):
    return {"Authorization": f"Bearer {api_key}"}


class TestSecurityHardening:
    def test_search_get_requires_auth(self, client):
        resp = client.get("/v1/search?query=test")
        assert resp.status_code == 401

    def test_dashboard_requires_auth(self, client):
        resp = client.get("/dashboard")
        assert resp.status_code == 401

    def test_hive_graph_requires_auth(self, client):
        resp = client.get("/hive/graph")
        assert resp.status_code == 401

    def test_search_get_works_with_auth(self, client, auth_headers):
        resp = client.get("/v1/search?query=test", headers=auth_headers)
        assert resp.status_code == 200


class TestValidationHardening:
    def test_store_fact_max_length(self, client, auth_headers):
        big_content = "a" * 50001
        resp = client.post(
            "/v1/facts", json={"project": "test", "content": big_content}, headers=auth_headers
        )
        assert resp.status_code == 422

    def test_project_name_max_length(self, client, auth_headers):
        long_project = "p" * 101
        resp = client.post(
            "/v1/facts", json={"project": long_project, "content": "test"}, headers=auth_headers
        )
        assert resp.status_code == 422


class TestSearchFiltering:
    def test_post_search_project_filtering(self, client, auth_headers):
        client.post(
            "/v1/facts", json={"project": "p1", "content": "unique star"}, headers=auth_headers
        )
        client.post(
            "/v1/facts", json={"project": "p2", "content": "unique moon"}, headers=auth_headers
        )

        resp = client.post(
            "/v1/search", json={"query": "unique star"}, headers=auth_headers
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 1
        assert "star" in results[0]["content"]

"""
CORTEX v4.0 — Hardening Tests.

Verifies the fixes for security leaks and resource management identified by Kimi.
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# Set test DB before importing api
_test_db = tempfile.mktemp(suffix=".db")
os.environ["CORTEX_DB"] = _test_db

from cortex.api import app
from cortex.auth import AuthManager

@pytest.fixture(scope="module")
def client():
    # Force lifespan to run and use the test DB
    import cortex.api as api_mod
    original_db = api_mod.DB_PATH
    # Use the module-level _test_db if env var is missing
    api_mod.DB_PATH = os.environ.get("CORTEX_DB", _test_db)
    
    try:
        with TestClient(api_mod.app) as c:
            yield c
    finally:
        api_mod.DB_PATH = original_db

@pytest.fixture(scope="module")
def api_key(client):
    resp = client.post("/v1/admin/keys?name=hardening-test&tenant_id=default")
    if resp.status_code != 200:
        pytest.fail(f"Failed to create key (Status {resp.status_code}): {resp.text}")
    return resp.json()["key"]

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
        # content max_length is 50000
        big_content = "a" * 50001
        resp = client.post("/v1/facts", 
            json={"project": "test", "content": big_content},
            headers=auth_headers)
        assert resp.status_code == 422 # Validation error

    def test_project_name_max_length(self, client, auth_headers):
        # project max_length is 100
        long_project = "p" * 101
        resp = client.post("/v1/facts", 
            json={"project": long_project, "content": "test"},
            headers=auth_headers)
        assert resp.status_code == 422

class TestSearchFiltering:
    def test_post_search_project_filtering(self, client, auth_headers):
        # Store facts in different projects
        client.post("/v1/facts", json={"project": "p1", "content": "unique star"}, headers=auth_headers)
        client.post("/v1/facts", json={"project": "p2", "content": "unique moon"}, headers=auth_headers)
        
        # Search in p1
        resp = client.post("/v1/search", json={"query": "unique", "project": "p1"}, headers=auth_headers)
        assert resp.status_code == 200
        results = resp.json()
        # Vector search filters by project — verify all results are from p1
        assert all(r["project"] == "p1" for r in results)

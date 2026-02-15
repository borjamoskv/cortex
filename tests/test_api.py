"""
CORTEX v4.0 — API Tests.

Tests for the FastAPI REST API endpoints.
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
    """Create test client with bootstrapped API key."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def api_key(client):
    """Bootstrap first API key."""
    resp = client.post("/v1/admin/keys?name=test-key&tenant_id=test")
    assert resp.status_code == 200
    return resp.json()["key"]


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
        resp = client.post("/v1/facts", json={
            "project": "test", "content": "hello"
        })
        assert resp.status_code == 401

    def test_bad_key_rejected(self, client):
        resp = client.post("/v1/facts",
            json={"project": "test", "content": "hello"},
            headers={"Authorization": "Bearer ctx_invalid"})
        assert resp.status_code == 401

    def test_good_key_accepted(self, client, auth_headers):
        resp = client.post("/v1/facts",
            json={"project": "test", "content": "hello"},
            headers=auth_headers)
        assert resp.status_code == 200


class TestFacts:
    def test_store(self, client, auth_headers):
        resp = client.post("/v1/facts",
            json={
                "project": "demo",
                "content": "CORTEX uses SQLite with vector search",
                "tags": ["tech", "db"],
            },
            headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["fact_id"] > 0

    def test_recall(self, client, auth_headers):
        resp = client.get("/v1/projects/demo/facts", headers=auth_headers)
        assert resp.status_code == 200
        facts = resp.json()
        assert len(facts) >= 1
        assert any("SQLite" in f["content"] for f in facts)

    def test_deprecate(self, client, auth_headers):
        # Store and deprecate
        store_resp = client.post("/v1/facts",
            json={"project": "demo", "content": "temporary fact"},
            headers=auth_headers)
        fact_id = store_resp.json()["fact_id"]

        resp = client.delete(f"/v1/facts/{fact_id}", headers=auth_headers)
        assert resp.status_code == 200

    def test_deprecate_nonexistent(self, client, auth_headers):
        resp = client.delete("/v1/facts/99999", headers=auth_headers)
        assert resp.status_code == 404


class TestSearch:
    def test_search(self, client, auth_headers):
        resp = client.post("/v1/search",
            json={"query": "database technology", "k": 3},
            headers=auth_headers)
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

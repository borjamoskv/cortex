"""Tests for dashboard and time-tracking endpoints."""

import os

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient


@pytest.fixture()
def dashboard_env(tmp_path):
    """Create isolated DB for each test to avoid connection locking."""
    db = str(tmp_path / "dashboard_test.db")
    os.environ["CORTEX_DB"] = db
    # Force fresh module state — reimport not needed because api reads env at lifespan
    yield db
    os.environ.pop("CORTEX_DB", None)


@pytest.fixture()
def client(dashboard_env):
    # Import here so CORTEX_DB env is set before the module-level DB_PATH reads it
    # We need to patch the DB_PATH directly since it's read at import time
    import cortex.api as api_mod

    original_db = api_mod.DB_PATH
    api_mod.DB_PATH = dashboard_env
    try:
        with TestClient(api_mod.app) as c:
            yield c, api_mod
    finally:
        api_mod.DB_PATH = original_db


def test_daily_method(client):
    """Test TimingTracker.daily() via the global tracker (lifespan-initialized)."""
    c, api_mod = client
    tracker = api_mod.app.state.tracker

    now = datetime.now(timezone.utc)

    # Day 0 (Today)
    tracker.heartbeat("proj1", "file1.py", timestamp=now.isoformat())
    tracker.heartbeat("proj1", "file1.py", timestamp=(now + timedelta(minutes=60)).isoformat())

    # Day -1 (Yesterday)
    d1 = now - timedelta(days=1)
    tracker.heartbeat("proj1", "file1.py", timestamp=d1.isoformat())
    tracker.heartbeat("proj1", "file1.py", timestamp=(d1 + timedelta(minutes=120)).isoformat())

    tracker.flush(gap_seconds=3600 * 5)

    stats = tracker.daily(days=3)
    assert len(stats) == 3
    assert stats[-1]["date"] == now.strftime("%Y-%m-%d")


def test_history_endpoint(client):
    c, api_mod = client
    # Create an API key for this test
    resp = c.post("/v1/admin/keys?name=test-key&tenant_id=test")
    api_key = resp.json()["key"]
    headers = {"Authorization": f"Bearer {api_key}"}

    resp = c.get("/v1/time/history?days=5", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 5

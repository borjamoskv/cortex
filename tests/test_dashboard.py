"""Tests for dashboard and time-tracking endpoints."""

import os
import tempfile

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

# Set test DB before importing api — use unique file to avoid _conn conflicts
_test_db = tempfile.mktemp(suffix="_dashboard.db")
os.environ["CORTEX_DB"] = _test_db

from cortex.api import app, tracker as global_tracker


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def api_key(client):
    resp = client.post("/v1/admin/keys?name=test-key&tenant_id=test")
    return resp.json()["key"]


@pytest.fixture(scope="module")
def auth_headers(api_key):
    return {"Authorization": f"Bearer {api_key}"}


def test_daily_method(client):
    """Test TimingTracker.daily() via the global tracker (lifespan-initialized)."""
    # client fixture ensures lifespan has run → global_tracker is ready
    tracker = global_tracker

    now = datetime.now(timezone.utc)

    # Day 0 (Today)
    tracker.heartbeat("proj1", "file1.py", timestamp=now.isoformat())
    tracker.heartbeat(
        "proj1", "file1.py", timestamp=(now + timedelta(minutes=60)).isoformat()
    )

    # Day -1 (Yesterday)
    d1 = now - timedelta(days=1)
    tracker.heartbeat("proj1", "file1.py", timestamp=d1.isoformat())
    tracker.heartbeat(
        "proj1", "file1.py", timestamp=(d1 + timedelta(minutes=120)).isoformat()
    )

    tracker.flush(gap_seconds=3600 * 5)

    stats = tracker.daily(days=3)
    assert len(stats) == 3
    assert stats[-1]["date"] == now.strftime("%Y-%m-%d")


def test_history_endpoint(client, auth_headers):
    resp = client.get("/v1/time/history?days=5", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 5

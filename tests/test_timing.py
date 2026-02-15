"""
CORTEX v4.0 — Time Tracking Tests.

Tests for heartbeat storage, flush to entries, reports, and classification.
"""

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from cortex.timing import TimingTracker, classify_entity


def _create_db() -> tuple[sqlite3.Connection, str]:
    """Create a temp DB with timing tables."""
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = f.name
    f.close()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")

    # Create timing tables
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS heartbeats (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        project     TEXT NOT NULL,
        entity      TEXT,
        category    TEXT NOT NULL,
        branch      TEXT,
        language    TEXT,
        timestamp   TEXT NOT NULL,
        meta        TEXT DEFAULT '{}'
    );

    CREATE TABLE IF NOT EXISTS time_entries (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        project     TEXT NOT NULL,
        category    TEXT NOT NULL,
        start_time  TEXT NOT NULL,
        end_time    TEXT NOT NULL,
        duration_s  INTEGER NOT NULL,
        entities    TEXT DEFAULT '[]',
        heartbeats  INTEGER DEFAULT 0,
        meta        TEXT DEFAULT '{}'
    );
    """)
    conn.commit()
    return conn, db_path


@pytest.fixture
def tracker():
    """Create a TimingTracker with a fresh temp DB."""
    conn, db_path = _create_db()
    t = TimingTracker(conn, gap_seconds=300)
    yield t
    conn.close()
    os.unlink(db_path)


# ─── Classification Tests ────────────────────────────────────────────


class TestClassification:
    def test_python_is_coding(self):
        assert classify_entity("engine.py") == "coding"

    def test_js_is_coding(self):
        assert classify_entity("app.js") == "coding"

    def test_css_is_coding(self):
        assert classify_entity("variables.css") == "coding"

    def test_markdown_is_docs(self):
        assert classify_entity("README.md") == "docs"

    def test_test_file_is_testing(self):
        assert classify_entity("test_engine.py") == "testing"

    def test_spec_file_is_testing(self):
        assert classify_entity("app.spec.ts") == "testing"

    def test_slack_is_comms(self):
        assert classify_entity("slack") == "comms"

    def test_unknown_is_other(self):
        assert classify_entity("something_random") == "other"

    def test_empty_is_other(self):
        assert classify_entity("") == "other"


# ─── Heartbeat Tests ──────────────────────────────────────────────────


class TestHeartbeat:
    def test_heartbeat_returns_id(self, tracker):
        hb_id = tracker.heartbeat("naroa-web", "css/variables.css")
        assert hb_id > 0

    def test_heartbeat_increments(self, tracker):
        id1 = tracker.heartbeat("naroa-web", "file1.py")
        id2 = tracker.heartbeat("naroa-web", "file2.py")
        assert id2 > id1

    def test_heartbeat_auto_classifies(self, tracker):
        tracker.heartbeat("test", "main.swift")
        row = tracker._conn.execute(
            "SELECT category FROM heartbeats WHERE id=1"
        ).fetchone()
        assert row[0] == "coding"

    def test_heartbeat_custom_category(self, tracker):
        tracker.heartbeat("test", "meeting", category="comms")
        row = tracker._conn.execute(
            "SELECT category FROM heartbeats WHERE id=1"
        ).fetchone()
        assert row[0] == "comms"

    def test_heartbeat_with_branch(self, tracker):
        tracker.heartbeat("test", "file.py", branch="feature/timing")
        row = tracker._conn.execute(
            "SELECT branch FROM heartbeats WHERE id=1"
        ).fetchone()
        assert row[0] == "feature/timing"


# ─── Flush Tests ──────────────────────────────────────────────────────


class TestFlush:
    def test_flush_creates_entry(self, tracker):
        now = datetime.now(timezone.utc)
        t1 = now.isoformat()
        t2 = (now + timedelta(minutes=2)).isoformat()

        tracker.heartbeat("proj", "a.py", timestamp=t1)
        tracker.heartbeat("proj", "b.py", timestamp=t2)

        entries = tracker.flush()
        assert entries == 1

    def test_flush_splits_on_gap(self, tracker):
        now = datetime.now(timezone.utc)
        t1 = now.isoformat()
        t2 = (now + timedelta(minutes=2)).isoformat()
        t3 = (now + timedelta(minutes=10)).isoformat()  # > 5 min gap

        tracker.heartbeat("proj", "a.py", timestamp=t1)
        tracker.heartbeat("proj", "b.py", timestamp=t2)
        tracker.heartbeat("proj", "c.py", timestamp=t3)

        entries = tracker.flush()
        assert entries == 2

    def test_flush_splits_on_category(self, tracker):
        now = datetime.now(timezone.utc)
        t1 = now.isoformat()
        t2 = (now + timedelta(minutes=1)).isoformat()

        tracker.heartbeat("proj", "a.py", timestamp=t1)  # coding
        tracker.heartbeat("proj", "README.md", timestamp=t2)  # docs

        entries = tracker.flush()
        assert entries == 2

    def test_flush_calculates_duration(self, tracker):
        now = datetime.now(timezone.utc)
        t1 = now.isoformat()
        t2 = (now + timedelta(minutes=3)).isoformat()

        tracker.heartbeat("proj", "a.py", timestamp=t1)
        tracker.heartbeat("proj", "b.py", timestamp=t2)
        tracker.flush()

        row = tracker._conn.execute(
            "SELECT duration_s FROM time_entries WHERE id=1"
        ).fetchone()
        assert row[0] == 180  # 3 minutes

    def test_flush_collects_entities(self, tracker):
        now = datetime.now(timezone.utc)
        t1 = now.isoformat()
        t2 = (now + timedelta(minutes=1)).isoformat()

        tracker.heartbeat("proj", "a.py", timestamp=t1)
        tracker.heartbeat("proj", "b.py", timestamp=t2)
        tracker.flush()

        row = tracker._conn.execute(
            "SELECT entities FROM time_entries WHERE id=1"
        ).fetchone()
        entities = json.loads(row[0])
        assert "a.py" in entities
        assert "b.py" in entities

    def test_flush_idempotent(self, tracker):
        now = datetime.now(timezone.utc)
        tracker.heartbeat("proj", "a.py", timestamp=now.isoformat())
        tracker.heartbeat("proj", "b.py", timestamp=(now + timedelta(minutes=1)).isoformat())

        tracker.flush()
        second_flush = tracker.flush()
        assert second_flush == 0  # No new heartbeats


# ─── Report Tests ─────────────────────────────────────────────────────


class TestReports:
    def test_today_empty(self, tracker):
        summary = tracker.today()
        assert summary.total_seconds == 0
        assert summary.entries == 0

    def test_today_with_data(self, tracker):
        now = datetime.now(timezone.utc)
        tracker.heartbeat("proj", "a.py", timestamp=now.isoformat())
        tracker.heartbeat("proj", "b.py", timestamp=(now + timedelta(minutes=3)).isoformat())
        tracker.flush()

        summary = tracker.today()
        assert summary.total_seconds == 180
        assert summary.entries == 1
        assert "coding" in summary.by_category
        assert "proj" in summary.by_project

    def test_report_by_project(self, tracker):
        now = datetime.now(timezone.utc)
        tracker.heartbeat("alpha", "a.py", timestamp=now.isoformat())
        tracker.heartbeat("alpha", "b.py", timestamp=(now + timedelta(minutes=2)).isoformat())
        tracker.heartbeat("beta", "c.py", timestamp=(now + timedelta(minutes=5)).isoformat())
        tracker.heartbeat("beta", "d.py", timestamp=(now + timedelta(minutes=7)).isoformat())
        tracker.flush()

        summary = tracker.report(project="alpha", days=1)
        assert "alpha" in summary.by_project
        assert "beta" not in summary.by_project

    def test_format_duration(self, tracker):
        summary = tracker.today()
        assert summary.format_duration(3661) == "1h 1m"
        assert summary.format_duration(300) == "5m"

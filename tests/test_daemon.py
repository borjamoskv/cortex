"""Tests for MOSKV-1 Daemon."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from cortex.daemon import (
    DaemonStatus,
    GhostAlert,
    GhostWatcher,
    MemoryAlert,
    MemorySyncer,
    MoskvDaemon,
    Notifier,
    SiteMonitor,
    SiteStatus,
)


# ─── SiteStatus ───────────────────────────────────────────────────────


class TestSiteStatus:
    def test_healthy_site(self):
        s = SiteStatus(url="https://example.com", healthy=True, status_code=200, response_ms=50.0)
        assert s.healthy is True
        assert s.status_code == 200

    def test_unhealthy_site(self):
        s = SiteStatus(url="https://down.com", healthy=False, error="timeout")
        assert s.healthy is False
        assert s.error == "timeout"


# ─── GhostWatcher ─────────────────────────────────────────────────────


class TestGhostWatcher:
    def test_no_file(self, tmp_path):
        watcher = GhostWatcher(ghosts_path=tmp_path / "nope.json")
        assert watcher.check() == []

    def test_detects_stale(self, tmp_path):
        ghosts_file = tmp_path / "ghosts.json"
        stale_time = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        ghosts_file.write_text(json.dumps({
            "old-project": {
                "last_task": "something",
                "timestamp": stale_time,
                "mood": "dormant",
                "blocked_by": None,
            }
        }))

        watcher = GhostWatcher(ghosts_path=ghosts_file, stale_hours=48)
        alerts = watcher.check()
        assert len(alerts) == 1
        assert alerts[0].project == "old-project"
        assert alerts[0].hours_stale > 48

    def test_ignores_recent(self, tmp_path):
        ghosts_file = tmp_path / "ghosts.json"
        recent = datetime.now(timezone.utc).isoformat()
        ghosts_file.write_text(json.dumps({
            "active-project": {
                "timestamp": recent,
                "blocked_by": None,
            }
        }))

        watcher = GhostWatcher(ghosts_path=ghosts_file, stale_hours=48)
        assert watcher.check() == []

    def test_ignores_blocked(self, tmp_path):
        ghosts_file = tmp_path / "ghosts.json"
        stale_time = (datetime.now(timezone.utc) - timedelta(hours=100)).isoformat()
        ghosts_file.write_text(json.dumps({
            "blocked-project": {
                "timestamp": stale_time,
                "blocked_by": "waiting for API key",
            }
        }))

        watcher = GhostWatcher(ghosts_path=ghosts_file, stale_hours=48)
        assert watcher.check() == []


# ─── MemorySyncer ─────────────────────────────────────────────────────


class TestMemorySyncer:
    def test_no_file(self, tmp_path):
        syncer = MemorySyncer(system_path=tmp_path / "nope.json")
        assert syncer.check() == []

    def test_detects_stale(self, tmp_path):
        sys_file = tmp_path / "system.json"
        stale_time = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
        sys_file.write_text(json.dumps({
            "meta": {"last_updated": stale_time}
        }))

        syncer = MemorySyncer(system_path=sys_file, stale_hours=24)
        alerts = syncer.check()
        assert len(alerts) == 1
        assert alerts[0].hours_stale > 24

    def test_fresh_is_ok(self, tmp_path):
        sys_file = tmp_path / "system.json"
        sys_file.write_text(json.dumps({
            "meta": {"last_updated": datetime.now(timezone.utc).isoformat()}
        }))

        syncer = MemorySyncer(system_path=sys_file, stale_hours=24)
        assert syncer.check() == []


# ─── DaemonStatus ─────────────────────────────────────────────────────


class TestDaemonStatus:
    def test_all_healthy(self):
        status = DaemonStatus(
            checked_at="2026-02-15T22:00:00Z",
            sites=[SiteStatus(url="https://example.com", healthy=True)],
        )
        assert status.all_healthy is True

    def test_unhealthy_site(self):
        status = DaemonStatus(
            checked_at="2026-02-15T22:00:00Z",
            sites=[SiteStatus(url="https://down.com", healthy=False)],
        )
        assert status.all_healthy is False

    def test_stale_ghost_unhealthy(self):
        status = DaemonStatus(
            checked_at="2026-02-15T22:00:00Z",
            stale_ghosts=[GhostAlert(project="x", last_activity="", hours_stale=72)],
        )
        assert status.all_healthy is False

    def test_to_dict(self):
        status = DaemonStatus(
            checked_at="2026-02-15T22:00:00Z",
            sites=[SiteStatus(url="https://ok.com", healthy=True, response_ms=42.3)],
        )
        d = status.to_dict()
        assert d["all_healthy"] is True
        assert d["sites"][0]["response_ms"] == 42.3


# ─── MoskvDaemon ──────────────────────────────────────────────────────


class TestMoskvDaemon:
    def test_check_with_mocked_monitors(self, tmp_path):
        """Integration test: run a check with real ghost + memory files."""
        ghosts = tmp_path / "ghosts.json"
        system = tmp_path / "system.json"

        # Create fresh data
        now = datetime.now(timezone.utc).isoformat()
        ghosts.write_text(json.dumps({
            "project-a": {"timestamp": now, "blocked_by": None}
        }))
        system.write_text(json.dumps({
            "meta": {"last_updated": now}
        }))

        daemon = MoskvDaemon(
            sites=["https://httpbin.org/status/200"],
            config_dir=tmp_path,
            notify=False,
        )

        with patch.object(daemon.site_monitor, "check_all", return_value=[
            SiteStatus(url="https://httpbin.org/status/200", healthy=True, status_code=200)
        ]):
            status = daemon.check()

        assert len(status.sites) == 1
        assert status.sites[0].healthy is True
        assert len(status.stale_ghosts) == 0
        assert len(status.memory_alerts) == 0

    def test_status_persistence(self, tmp_path):
        """Verify status is written to and read from disk."""
        import cortex.daemon as daemon_mod
        original = daemon_mod.STATUS_FILE

        try:
            daemon_mod.STATUS_FILE = tmp_path / "daemon_status.json"

            daemon = MoskvDaemon(
                sites=[],
                config_dir=tmp_path,
                notify=False,
            )

            # Create minimal files
            (tmp_path / "ghosts.json").write_text("{}")
            (tmp_path / "system.json").write_text(json.dumps({
                "meta": {"last_updated": datetime.now(timezone.utc).isoformat()}
            }))

            with patch.object(daemon.site_monitor, "check_all", return_value=[]):
                daemon.check()

            loaded = MoskvDaemon.load_status()
            assert loaded is not None
            assert "checked_at" in loaded
        finally:
            daemon_mod.STATUS_FILE = original


# ─── Notifier ─────────────────────────────────────────────────────────


class TestNotifier:
    @patch("subprocess.run")
    def test_notify_calls_osascript(self, mock_run):
        result = Notifier.notify("Test", "Hello")
        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args
        assert args[0][0][0] == "osascript"

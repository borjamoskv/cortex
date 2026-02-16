"""Tests for MOSKV-1 Daemon."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import httpx

from cortex.daemon import (
    CertAlert,
    CertMonitor,
    DaemonStatus,
    DiskAlert,
    DiskMonitor,
    EngineHealthAlert,
    EngineHealthCheck,
    GhostAlert,
    GhostWatcher,
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
        ghosts_file.write_text(
            json.dumps(
                {
                    "old-project": {
                        "last_task": "something",
                        "timestamp": stale_time,
                        "mood": "dormant",
                        "blocked_by": None,
                    }
                }
            )
        )

        watcher = GhostWatcher(ghosts_path=ghosts_file, stale_hours=48)
        alerts = watcher.check()
        assert len(alerts) == 1
        assert alerts[0].project == "old-project"
        assert alerts[0].hours_stale > 48

    def test_ignores_recent(self, tmp_path):
        ghosts_file = tmp_path / "ghosts.json"
        recent = datetime.now(timezone.utc).isoformat()
        ghosts_file.write_text(
            json.dumps(
                {
                    "active-project": {
                        "timestamp": recent,
                        "blocked_by": None,
                    }
                }
            )
        )

        watcher = GhostWatcher(ghosts_path=ghosts_file, stale_hours=48)
        assert watcher.check() == []

    def test_ignores_blocked(self, tmp_path):
        ghosts_file = tmp_path / "ghosts.json"
        stale_time = (datetime.now(timezone.utc) - timedelta(hours=100)).isoformat()
        ghosts_file.write_text(
            json.dumps(
                {
                    "blocked-project": {
                        "timestamp": stale_time,
                        "blocked_by": "waiting for API key",
                    }
                }
            )
        )

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
        sys_file.write_text(json.dumps({"meta": {"last_updated": stale_time}}))

        syncer = MemorySyncer(system_path=sys_file, stale_hours=24)
        alerts = syncer.check()
        assert len(alerts) == 1
        assert alerts[0].hours_stale > 24

    def test_fresh_is_ok(self, tmp_path):
        sys_file = tmp_path / "system.json"
        sys_file.write_text(
            json.dumps({"meta": {"last_updated": datetime.now(timezone.utc).isoformat()}})
        )

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

    def test_to_dict_includes_duration(self):
        status = DaemonStatus(checked_at="now", check_duration_ms=123.456)
        d = status.to_dict()
        assert d["check_duration_ms"] == 123.5

    def test_cert_alert_makes_unhealthy(self):
        status = DaemonStatus(
            checked_at="now",
            cert_alerts=[CertAlert(hostname="example.com", expires_at="soon", days_remaining=5)],
        )
        assert status.all_healthy is False

    def test_engine_alert_makes_unhealthy(self):
        status = DaemonStatus(
            checked_at="now",
            engine_alerts=[EngineHealthAlert(issue="database_missing")],
        )
        assert status.all_healthy is False

    def test_disk_alert_makes_unhealthy(self):
        status = DaemonStatus(
            checked_at="now",
            disk_alerts=[DiskAlert(path="/tmp", size_mb=600, threshold_mb=500)],
        )
        assert status.all_healthy is False

    def test_to_dict_with_new_alerts(self):
        status = DaemonStatus(
            checked_at="now",
            cert_alerts=[CertAlert(hostname="x.com", expires_at="soon", days_remaining=3)],
            engine_alerts=[EngineHealthAlert(issue="db_missing", detail="gone")],
            disk_alerts=[DiskAlert(path="/tmp", size_mb=700.7, threshold_mb=500)],
        )
        d = status.to_dict()
        assert d["cert_alerts"][0]["days_remaining"] == 3
        assert d["engine_alerts"][0]["issue"] == "db_missing"
        assert d["disk_alerts"][0]["size_mb"] == 700.7


# ─── SiteMonitor Retry ────────────────────────────────────────────────


class TestSiteMonitorRetry:
    @patch("cortex.daemon.time.sleep")  # skip real sleep
    @patch("httpx.get")
    def test_retry_on_timeout_then_success(self, mock_get, mock_sleep):
        """First call times out, second succeeds."""
        ok_response = MagicMock()
        ok_response.status_code = 200
        mock_get.side_effect = [httpx.TimeoutException("slow"), ok_response]

        monitor = SiteMonitor(["https://x.com"], retries=1)
        results = monitor.check_all()
        assert len(results) == 1
        assert results[0].healthy is True
        assert mock_get.call_count == 2

    @patch("cortex.daemon.time.sleep")
    @patch("httpx.get")
    def test_all_retries_fail(self, mock_get, mock_sleep):
        """Both attempts fail — returns unhealthy."""
        mock_get.side_effect = httpx.ConnectError("refused")

        monitor = SiteMonitor(["https://x.com"], retries=1)
        results = monitor.check_all()
        assert results[0].healthy is False
        assert results[0].error == "connection refused"
        assert mock_get.call_count == 2

    @patch("httpx.get")
    def test_no_retry_on_success(self, mock_get):
        """Success on first try — no retry needed."""
        ok_response = MagicMock()
        ok_response.status_code = 200
        mock_get.return_value = ok_response

        monitor = SiteMonitor(["https://x.com"], retries=1)
        results = monitor.check_all()
        assert results[0].healthy is True
        assert mock_get.call_count == 1


# ─── EngineHealthCheck ────────────────────────────────────────────────


class TestEngineHealthCheck:
    def test_missing_db(self, tmp_path):
        check = EngineHealthCheck(db_path=tmp_path / "nonexistent.db")
        alerts = check.check()
        assert len(alerts) == 1
        assert alerts[0].issue == "database_missing"

    def test_empty_db(self, tmp_path):
        db = tmp_path / "cortex.db"
        db.write_bytes(b"")
        check = EngineHealthCheck(db_path=db)
        alerts = check.check()
        assert any(a.issue == "database_empty" for a in alerts)

    def test_healthy_db(self, tmp_path):
        db = tmp_path / "cortex.db"
        db.write_bytes(b"SQLite format 3\x00" + b"\x00" * 100)
        check = EngineHealthCheck(db_path=db)
        assert check.check() == []


# ─── DiskMonitor ──────────────────────────────────────────────────────


class TestDiskMonitor:
    def test_under_threshold(self, tmp_path):
        (tmp_path / "small.txt").write_text("hello")
        monitor = DiskMonitor(watch_path=tmp_path, threshold_mb=1)
        assert monitor.check() == []

    def test_over_threshold(self, tmp_path):
        # Write 2MB of data
        big = tmp_path / "big.bin"
        big.write_bytes(b"\x00" * (2 * 1024 * 1024))
        monitor = DiskMonitor(watch_path=tmp_path, threshold_mb=1)
        alerts = monitor.check()
        assert len(alerts) == 1
        assert alerts[0].size_mb > 1

    def test_nonexistent_path(self, tmp_path):
        monitor = DiskMonitor(watch_path=tmp_path / "nope", threshold_mb=1)
        assert monitor.check() == []


# ─── CertMonitor ──────────────────────────────────────────────────────


class TestCertMonitor:
    @patch("cortex.daemon.socket.create_connection")
    @patch("cortex.daemon.ssl.create_default_context")
    def test_expiring_cert(self, mock_ctx, mock_conn):
        """Cert expiring in 5 days should trigger alert."""
        expires = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%b %d %H:%M:%S %Y GMT")
        mock_ssock = MagicMock()
        mock_ssock.getpeercert.return_value = {"notAfter": expires}
        mock_ssock.__enter__ = lambda s: s
        mock_ssock.__exit__ = MagicMock(return_value=False)

        mock_sock = MagicMock()
        mock_sock.__enter__ = lambda s: s
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value = mock_sock

        mock_ctx.return_value.wrap_socket.return_value = mock_ssock

        monitor = CertMonitor(["example.com"], warn_days=14)
        alerts = monitor.check()
        assert len(alerts) == 1
        assert alerts[0].days_remaining < 14

    @patch("cortex.daemon.socket.create_connection")
    @patch("cortex.daemon.ssl.create_default_context")
    def test_valid_cert(self, mock_ctx, mock_conn):
        """Cert expiring in 90 days should NOT trigger alert."""
        expires = (datetime.now(timezone.utc) + timedelta(days=90)).strftime(
            "%b %d %H:%M:%S %Y GMT"
        )
        mock_ssock = MagicMock()
        mock_ssock.getpeercert.return_value = {"notAfter": expires}
        mock_ssock.__enter__ = lambda s: s
        mock_ssock.__exit__ = MagicMock(return_value=False)

        mock_sock = MagicMock()
        mock_sock.__enter__ = lambda s: s
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value = mock_sock

        mock_ctx.return_value.wrap_socket.return_value = mock_ssock

        monitor = CertMonitor(["example.com"], warn_days=14)
        assert monitor.check() == []


# ─── Cooldown ─────────────────────────────────────────────────────────


class TestCooldown:
    def test_alert_cooldown(self, tmp_path):
        """Same alert key should be rate-limited by cooldown."""
        (tmp_path / "ghosts.json").write_text("{}")
        (tmp_path / "system.json").write_text(
            json.dumps({"meta": {"last_updated": datetime.now(timezone.utc).isoformat()}})
        )

        daemon = MoskvDaemon(sites=[], config_dir=tmp_path, notify=True, cooldown=3600)
        # First call → should alert
        assert daemon._should_alert("test:key") is True
        # Second call immediately → should NOT alert (cooldown)
        assert daemon._should_alert("test:key") is False
        # Different key → should alert
        assert daemon._should_alert("test:other") is True


# ─── Check Duration ──────────────────────────────────────────────────


class TestCheckDuration:
    def test_check_records_duration(self, tmp_path):
        """check() should record check_duration_ms > 0."""
        import cortex.daemon as daemon_mod

        original = daemon_mod.STATUS_FILE

        try:
            daemon_mod.STATUS_FILE = tmp_path / "status.json"

            (tmp_path / "ghosts.json").write_text("{}")
            (tmp_path / "system.json").write_text(
                json.dumps({"meta": {"last_updated": datetime.now(timezone.utc).isoformat()}})
            )

            daemon = MoskvDaemon(sites=[], config_dir=tmp_path, notify=False)
            with patch.object(daemon.site_monitor, "check_all", return_value=[]):
                status = daemon.check()

            assert status.check_duration_ms > 0
        finally:
            daemon_mod.STATUS_FILE = original


# ─── MoskvDaemon ──────────────────────────────────────────────────────


class TestMoskvDaemon:
    def test_check_with_mocked_monitors(self, tmp_path):
        """Integration test: run a check with real ghost + memory files."""
        ghosts = tmp_path / "ghosts.json"
        system = tmp_path / "system.json"

        # Create fresh data
        now = datetime.now(timezone.utc).isoformat()
        ghosts.write_text(json.dumps({"project-a": {"timestamp": now, "blocked_by": None}}))
        system.write_text(json.dumps({"meta": {"last_updated": now}}))

        daemon = MoskvDaemon(
            sites=["https://httpbin.org/status/200"],
            config_dir=tmp_path,
            notify=False,
        )

        with patch.object(
            daemon.site_monitor,
            "check_all",
            return_value=[
                SiteStatus(url="https://httpbin.org/status/200", healthy=True, status_code=200)
            ],
        ):
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
            (tmp_path / "system.json").write_text(
                json.dumps({"meta": {"last_updated": datetime.now(timezone.utc).isoformat()}})
            )

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

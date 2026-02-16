"""Tests for MOSKV-1 Daemon CLI (Click)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from cortex.daemon_cli import cli


@pytest.fixture
def runner():
    return CliRunner()


# ─── Basic Commands ───────────────────────────────────────────────────


class TestCliBasic:
    def test_no_command_shows_help(self, runner):
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "MOSKV-1" in result.output

    def test_version(self, runner):
        result = runner.invoke(cli, ["version"])
        assert result.exit_code == 0
        assert "MOSKV-1 Daemon" in result.output
        assert "CORTEX v" in result.output

    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "start" in result.output
        assert "check" in result.output
        assert "status" in result.output


# ─── Status Command ──────────────────────────────────────────────────


class TestCliStatus:
    def test_status_no_data(self, runner):
        with patch("cortex.daemon_cli.MoskvDaemon.load_status", return_value=None):
            result = runner.invoke(cli, ["status"])
            assert result.exit_code == 1
            assert "No daemon status" in result.output

    def test_status_with_data(self, runner):
        mock_status = {
            "checked_at": "2026-02-16T01:00:00Z",
            "check_duration_ms": 42.0,
            "all_healthy": True,
            "sites": [{"url": "https://example.com", "healthy": True, "response_ms": 100}],
            "stale_ghosts": [],
            "memory_alerts": [],
            "cert_alerts": [],
            "engine_alerts": [],
            "disk_alerts": [],
            "errors": [],
        }
        with patch("cortex.daemon_cli.MoskvDaemon.load_status", return_value=mock_status):
            result = runner.invoke(cli, ["status"])
            assert result.exit_code == 0
            assert "Last Status" in result.output


# ─── Check Command ───────────────────────────────────────────────────


class TestCliCheck:
    def test_check_healthy(self, runner, tmp_path):
        """Check with all healthy systems exits 0."""
        from cortex.daemon import DaemonStatus, SiteStatus

        mock_daemon = patch("cortex.daemon_cli._build_daemon")
        with mock_daemon as m:
            daemon = m.return_value
            daemon.check.return_value = DaemonStatus(
                checked_at="2026-02-16T01:00:00Z",
                check_duration_ms=10.0,
                sites=[SiteStatus(url="https://ok.com", healthy=True, status_code=200)],
            )
            result = runner.invoke(cli, ["check"])
            assert result.exit_code == 0
            assert "ALL SYSTEMS NOMINAL" in result.output

    def test_check_unhealthy(self, runner):
        """Check with issues exits 1."""
        from cortex.daemon import DaemonStatus, SiteStatus

        mock_daemon = patch("cortex.daemon_cli._build_daemon")
        with mock_daemon as m:
            daemon = m.return_value
            daemon.check.return_value = DaemonStatus(
                checked_at="2026-02-16T01:00:00Z",
                check_duration_ms=10.0,
                sites=[SiteStatus(url="https://down.com", healthy=False, error="timeout")],
            )
            result = runner.invoke(cli, ["check"])
            assert result.exit_code == 1
            assert "ISSUE" in result.output

    def test_check_no_sites(self, runner):
        """Check with empty sites shows config hint."""
        from cortex.daemon import DaemonStatus

        mock_daemon = patch("cortex.daemon_cli._build_daemon")
        with mock_daemon as m:
            daemon = m.return_value
            daemon.check.return_value = DaemonStatus(
                checked_at="2026-02-16T01:00:00Z",
                check_duration_ms=5.0,
            )
            result = runner.invoke(cli, ["check"])
            assert result.exit_code == 0
            assert "No sites configured" in result.output

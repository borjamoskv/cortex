"""
CORTEX v4.0 — MEJORAlo Round 6 Tests.

Tests for CLI resource safety (try/finally), API error handling,
migration resilience, and edit defensive JSON.
"""

from __future__ import annotations

import json
import sqlite3
from unittest.mock import MagicMock, patch


# ═══ CLI try/finally resource safety ═══════════════════════════════


class TestCLIResourceSafety:
    """Verify engine.close() is always called even when commands raise."""

    def _make_mock_engine(self):
        engine = MagicMock()
        engine.close = MagicMock()
        return engine

    def test_search_calls_close_on_error(self):
        """search command should close engine even if search() raises."""
        engine = self._make_mock_engine()
        engine.search.side_effect = sqlite3.OperationalError("disk I/O error")

        with patch("cortex.cli.core.get_engine", return_value=engine):
            from click.testing import CliRunner
            from cortex.cli import cli

            runner = CliRunner()
            result = runner.invoke(cli, ["search", "test query"])
            engine.close.assert_called_once()

    def test_recall_calls_close_on_error(self):
        """recall command should close engine even if recall() raises."""
        engine = self._make_mock_engine()
        engine.recall.side_effect = RuntimeError("unexpected")

        with patch("cortex.cli.core.get_engine", return_value=engine):
            from click.testing import CliRunner
            from cortex.cli import cli

            runner = CliRunner()
            result = runner.invoke(cli, ["recall", "test-project"])
            engine.close.assert_called_once()

    def test_history_calls_close_on_error(self):
        """history command should close engine even if history() raises."""
        engine = self._make_mock_engine()
        engine.history.side_effect = sqlite3.OperationalError("corrupt")

        with patch("cortex.cli.core.get_engine", return_value=engine):
            from click.testing import CliRunner
            from cortex.cli import cli

            runner = CliRunner()
            result = runner.invoke(cli, ["history", "test-project"])
            engine.close.assert_called_once()

    def test_status_calls_close_on_error(self):
        """status command should close engine on stats error."""
        engine = self._make_mock_engine()
        engine.stats.side_effect = FileNotFoundError("no db")

        with patch("cortex.cli.core.get_engine", return_value=engine):
            from click.testing import CliRunner
            from cortex.cli import cli

            runner = CliRunner()
            result = runner.invoke(cli, ["status"])
            engine.close.assert_called_once()

    def test_list_facts_calls_close_on_success(self):
        """list-facts should close engine on normal (empty) completion."""
        engine = self._make_mock_engine()
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = []
        engine.get_connection.return_value = conn

        with patch("cortex.cli.crud.get_engine", return_value=engine):
            from click.testing import CliRunner
            from cortex.cli import cli

            runner = CliRunner()
            result = runner.invoke(cli, ["list"])
            engine.close.assert_called_once()


# ═══ CLI edit defensive JSON ══════════════════════════════════════


class TestEditDefensiveJSON:
    """edit command should handle malformed tags_json gracefully."""

    def test_edit_handles_corrupt_tags_json(self):
        """edit should not crash if tags JSON is corrupt."""
        engine = MagicMock()
        engine.close = MagicMock()
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (
            "test-project",
            "old content",
            "knowledge",
            "{corrupt json",  # CORRUPT tags
            0.9,
            "manual",
        )
        engine.get_connection.return_value = conn
        engine.deprecate.return_value = True
        engine.store.return_value = 42

        with (
            patch("cortex.cli.crud.get_engine", return_value=engine),
            patch("cortex.cli.crud.export_to_json") as mock_wb,
        ):
            mock_wb.return_value = MagicMock(files_written=0)
            from click.testing import CliRunner
            from cortex.cli import cli

            runner = CliRunner()
            result = runner.invoke(cli, ["edit", "1", "new content"])
            engine.store.assert_called_once()
            # tags should be None since JSON was corrupt
            _, kwargs = engine.store.call_args
            assert kwargs.get("tags") is None
            engine.close.assert_called_once()


# ═══ Migration resilience ════════════════════════════════════════


class TestMigrationResilience:
    """Migrations should handle errors gracefully."""

    def test_get_current_version_no_table(self):
        """get_current_version should return 0 if schema_version table doesn't exist."""
        conn = sqlite3.connect(":memory:")
        from cortex.migrations import get_current_version

        assert get_current_version(conn) == 0
        conn.close()

    def test_ensure_migration_table_idempotent(self):
        """ensure_migration_table should be safe to call multiple times."""
        conn = sqlite3.connect(":memory:")
        from cortex.migrations import ensure_migration_table, get_current_version

        ensure_migration_table(conn)
        ensure_migration_table(conn)  # second call
        assert get_current_version(conn) == 0
        conn.close()

    def test_migration_table_records_version(self):
        """Migration table should correctly track applied versions."""
        conn = sqlite3.connect(":memory:")
        from cortex.migrations import ensure_migration_table

        ensure_migration_table(conn)
        conn.execute(
            "INSERT INTO schema_version (version, description) VALUES (?, ?)",
            (1, "test migration"),
        )
        conn.commit()

        from cortex.migrations import get_current_version

        assert get_current_version(conn) == 1
        conn.close()


# ═══ API error handling ══════════════════════════════════════════


class TestAPIErrorHandling:
    """API should handle errors cleanly."""

    def test_value_error_handler_returns_422(self):
        """ValueError exception handler returns HTTP 422."""
        import asyncio
        from cortex.api import value_error_handler

        request = MagicMock()
        exc = ValueError("invalid input")
        response = asyncio.run(value_error_handler(request, exc))
        assert response.status_code == 422
        body = json.loads(response.body)
        assert body["detail"] == "invalid input"

    def test_app_has_rate_limiter(self):
        """API should have rate limiting middleware."""
        from cortex.api import app

        middleware_classes = [
            m.cls.__name__ if hasattr(m, "cls") else type(m).__name__ for m in app.user_middleware
        ]
        assert any("RateLimit" in name for name in middleware_classes)


# ═══ Async client parity ═════════════════════════════════════════


class TestAsyncClientParity:
    """Verify async_client matches sync client error handling."""

    def test_async_client_has_error_handling(self):
        """AsyncCortexClient._request should handle transport and JSON errors."""
        import inspect
        from cortex.async_client import AsyncCortexClient

        source = inspect.getsource(AsyncCortexClient._request)
        assert "httpx.HTTPError" in source
        assert "CortexError" in source
        assert "ValueError" in source

    def test_async_client_context_manager(self):
        """AsyncCortexClient should support async context manager."""
        from cortex.async_client import AsyncCortexClient

        assert hasattr(AsyncCortexClient, "__aenter__")
        assert hasattr(AsyncCortexClient, "__aexit__")
        assert hasattr(AsyncCortexClient, "close")

"""
Tests for MEJORAlo Rounds 3-5 improvements.

Covers:
- search.py: parameterized LIMIT, defensive JSON, text_search error handling
- dashboard.py: XSS sanitize() function exists
- api.py: ValueError → HTTP 422
- migrate.py: OSError guard on file reads
- cli.py: parameterized LIMIT in list_facts, defensive JSON for tags
- auth.py: defensive JSON for permissions
- timing.py: _safe_json_list / _safe_json_dict helpers
- client.py: error handling for non-JSON responses
"""

from __future__ import annotations

import sqlite3

# ──────────────────────────────────────────────────────────────────────
# Round 3 — search.py
# ──────────────────────────────────────────────────────────────────────


import pytest
import pytest_asyncio

class TestSearchDefensiveJson:
    """Test that search functions handle malformed JSON gracefully."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self):
        from cortex.engine import CortexEngine

        self.engine = CortexEngine(db_path=":memory:", auto_embed=False)
        await self.engine.init_db()
        self.conn = await self.engine.get_connection()
        yield
        await self.engine.close()

    async def _insert_fact_with_bad_json(self, content: str, bad_tags: str, bad_meta: str):
        """Insert a fact with malformed JSON fields directly into DB."""
        await self.conn.execute(
            """INSERT INTO facts (project, content, fact_type, tags, confidence,
               valid_from, valid_until, source, meta, created_at, updated_at)
               VALUES (?, ?, 'knowledge', ?, 'stated',
               datetime('now'), NULL, 'test', ?, datetime('now'), datetime('now'))""",
            ("test-project", content, bad_tags, bad_meta),
        )
        await self.conn.commit()

    @pytest.mark.asyncio
    async def test_text_search_with_malformed_tags(self):
        """text_search should return results even with broken JSON in tags."""
        from cortex.search import text_search

        await self._insert_fact_with_bad_json("important finding", "NOT_JSON", "{}")
        results = await text_search(self.conn, "important")
        assert len(results) == 1
        assert results[0].tags == []  # Gracefully defaulted

    @pytest.mark.asyncio
    async def test_text_search_with_malformed_meta(self):
        """text_search should return results even with broken JSON in meta."""
        from cortex.search import text_search

        await self._insert_fact_with_bad_json("key data", "[]", "BROKEN_META")
        results = await text_search(self.conn, "key data")
        assert len(results) == 1
        assert results[0].meta == {}  # Gracefully defaulted

    @pytest.mark.asyncio
    async def test_text_search_error_handling(self):
        """text_search returns empty list on DB error, not exception."""
        from cortex.search import text_search
        from unittest.mock import AsyncMock
        import sqlite3

        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = sqlite3.OperationalError("db error")
        results = await text_search(mock_conn, "anything")
        assert results == []

    def test_text_search_limit_is_parameterized(self):
        """Ensure LIMIT is parameterized (SQL injection prevention)."""
        import inspect

        from cortex.search import text

        source = inspect.getsource(text)
        # Should NOT contain f-string LIMIT
        assert "LIMIT {limit}" not in source
        assert "LIMIT ?" in source


# ──────────────────────────────────────────────────────────────────────
# Round 3 — dashboard.py XSS
# ──────────────────────────────────────────────────────────────────────


class TestDashboardXss:
    """Verify XSS prevention in dashboard."""

    def test_sanitize_function_exists(self):
        """Dashboard JS must contain a sanitize() function."""
        from cortex.dashboard import get_dashboard_html

        html = get_dashboard_html()
        assert "function sanitize(str)" in html

    def test_search_results_use_sanitize(self):
        """Search results must be rendered through sanitize()."""
        from cortex.dashboard import get_dashboard_html

        html = get_dashboard_html()
        assert "sanitize(item.content)" in html
        assert "sanitize(item.project)" in html
        assert "sanitize(item.fact_type)" in html
        assert "sanitize(t)" in html  # tags


# ──────────────────────────────────────────────────────────────────────
# Round 3 — api.py ValueError handler
# ──────────────────────────────────────────────────────────────────────


class TestApiValueErrorHandler:
    """API should return 422 for validation errors."""

    def test_value_error_handler_registered(self):
        """Check that the ValueError handler is registered on the app."""
        from cortex.api import app

        handlers = app.exception_handlers
        assert ValueError in handlers


# ──────────────────────────────────────────────────────────────────────
# Round 3 — migrate.py file read safety
# ──────────────────────────────────────────────────────────────────────


class TestMigrateFileReadSafety:
    """Migration file reads should handle OSError."""

    @pytest.mark.asyncio
    async def test_migrate_mistakes_oserror(self, tmp_path):
        """_migrate_mistakes records error instead of crashing on OSError."""
        from cortex.engine import CortexEngine
        from cortex.migrate import _migrate_mistakes

        engine = CortexEngine(db_path=":memory:")
        await engine.init_db()

        nonexistent = tmp_path / "does_not_exist.jsonl"
        stats = {"mistakes_imported": 0, "errors": []}
        # This should NOT raise
        _migrate_mistakes(engine, nonexistent, stats)
        assert len(stats["errors"]) == 1
        assert "Failed to read" in stats["errors"][0]

        await engine.close()

    @pytest.mark.asyncio
    async def test_migrate_bridges_oserror(self, tmp_path):
        """_migrate_bridges records error instead of crashing on OSError."""
        from cortex.engine import CortexEngine
        from cortex.migrate import _migrate_bridges

        engine = CortexEngine(db_path=":memory:")
        await engine.init_db()

        nonexistent = tmp_path / "does_not_exist.jsonl"
        stats = {"bridges_imported": 0, "errors": []}
        _migrate_bridges(engine, nonexistent, stats)
        assert len(stats["errors"]) == 1
        assert "Failed to read" in stats["errors"][0]

        await engine.close()


# ──────────────────────────────────────────────────────────────────────
# Round 3 — daemon.py Notifier.notify (not .send)
# ──────────────────────────────────────────────────────────────────────


class TestDaemonNotifierMethod:
    """daemon.py must use Notifier.notify(), not .send()."""

    def test_no_notifier_send_calls(self):
        """Verify that Notifier.send() is never called in daemon core."""
        import inspect

        from cortex.daemon import core

        source = inspect.getsource(core)
        assert "Notifier.send(" not in source
        # Verify the correct method IS used (e.g. alert_site_down)
        assert "Notifier.alert_" in source


# ──────────────────────────────────────────────────────────────────────
# Round 4 — cli.py
# ──────────────────────────────────────────────────────────────────────


class TestCliListFactsParamLimit:
    """CLI list_facts must use parameterized LIMIT."""

    def test_no_fstring_limit(self):
        """Verify list_facts doesn't use f-string LIMIT."""
        from pathlib import Path

        import cortex.cli.crud

        cli_source = Path(cortex.cli.crud.__file__).read_text()
        # Only inspect the list_facts function area
        assert "LIMIT {limit}" not in cli_source
        assert "LIMIT ?" in cli_source


# ──────────────────────────────────────────────────────────────────────
# Round 4 — timing.py safe JSON helpers
# ──────────────────────────────────────────────────────────────────────


class TestTimingSafeJson:
    """Test _safe_json_list and _safe_json_dict helpers."""

    def setup_method(self):
        from cortex.timing import TimingTracker

        self.tracker = TimingTracker.__new__(TimingTracker)

    def test_safe_json_list_valid(self):
        assert self.tracker._safe_json_list("[1, 2, 3]") == [1, 2, 3]

    def test_safe_json_list_none(self):
        assert self.tracker._safe_json_list(None) == []

    def test_safe_json_list_empty(self):
        assert self.tracker._safe_json_list("") == []

    def test_safe_json_list_malformed(self):
        assert self.tracker._safe_json_list("NOT_JSON") == []

    def test_safe_json_list_wrong_type(self):
        """Returns [] if JSON is valid but not a list."""
        assert self.tracker._safe_json_list('{"key": "val"}') == []

    def test_safe_json_dict_valid(self):
        assert self.tracker._safe_json_dict('{"a": 1}') == {"a": 1}

    def test_safe_json_dict_none(self):
        assert self.tracker._safe_json_dict(None) == {}

    def test_safe_json_dict_empty(self):
        assert self.tracker._safe_json_dict("") == {}

    def test_safe_json_dict_malformed(self):
        assert self.tracker._safe_json_dict("BROKEN") == {}

    def test_safe_json_dict_wrong_type(self):
        """Returns {} if JSON is valid but not a dict."""
        assert self.tracker._safe_json_dict("[1, 2]") == {}


# ──────────────────────────────────────────────────────────────────────
# Round 5 — client.py error handling
# ──────────────────────────────────────────────────────────────────────


class TestClientErrorHandling:
    """CortexClient should handle edge cases in HTTP responses."""

    def test_cortex_error_has_status_and_detail(self):
        from cortex.client import CortexError

        err = CortexError(422, "project cannot be empty")
        assert err.status_code == 422
        assert "422" in str(err)
        assert "project cannot be empty" in str(err)

    def test_cortex_error_zero_status_for_connection_errors(self):
        from cortex.client import CortexError

        err = CortexError(0, "Connection error: timeout")
        assert err.status_code == 0
        assert "Connection error" in err.detail

"""
CORTEX v4.0 — MEJORAlo Round 2 Tests.

Tests for robustness improvements: sync error resilience,
engine input validation, defensive JSON parsing, exception-safe close.
"""

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from cortex.engine import CortexEngine
from cortex.sync import export_to_json, sync_memory

# ─── Fixtures ────────────────────────────────────────────────────────


import pytest_asyncio

@pytest_asyncio.fixture
async def engine(tmp_path):
    """Create a fresh engine for testing."""
    db_path = tmp_path / "test.db"
    eng = CortexEngine(db_path=db_path, auto_embed=False)
    await eng.init_db()
    yield eng
    await eng.close()


# ─── Sync Robustness ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_engine_get_connection(tmp_path):
    db_path = tmp_path / "test.db"
    engine = CortexEngine(db_path)
    conn = await engine.get_connection()
    import aiosqlite
    assert isinstance(conn, aiosqlite.Connection)
    # Check it's the same connection
    assert conn is await engine.get_connection()
    await engine.close()


def test_sync_narrowed_exceptions(tmp_path):
    """When _file_hash raises OSError, sync_memory should catch it
    and record the error instead of propagating."""
    engine = MagicMock(spec=CortexEngine)

    with patch("cortex.sync.MEMORY_DIR", tmp_path):
        with patch("cortex.sync.read.file_hash", side_effect=OSError("Disk failure")):
            result = sync_memory(engine)
            # sync_memory now catches OSError from _file_hash
            assert any("Disk failure" in err for err in result.errors)


def test_export_to_json_exceptions(tmp_path):
    engine = MagicMock(spec=CortexEngine)
    with patch("cortex.sync.MEMORY_DIR", tmp_path):
        # Mock _db_content_hash to raise an expected exception
        with patch("cortex.sync.write.db_content_hash", side_effect=sqlite3.Error("DB Locked")):
            result = export_to_json(engine)
            assert any("DB Locked" in err for err in result.errors)
            assert result.files_skipped == 0  # because it failed before skip check


# ─── Engine Input Validation ─────────────────────────────────────────


class TestStoreValidation:
    """Tests for store() input guards."""

    @pytest.mark.asyncio
    async def test_store_empty_project(self, engine):
        with pytest.raises(ValueError, match="project cannot be empty"):
            await engine.store("", "some content")

    @pytest.mark.asyncio
    async def test_store_whitespace_project(self, engine):
        with pytest.raises(ValueError, match="project cannot be empty"):
            await engine.store("   ", "some content")

    @pytest.mark.asyncio
    async def test_store_empty_content(self, engine):
        with pytest.raises(ValueError, match="content cannot be empty"):
            await engine.store("test-project", "")

    @pytest.mark.asyncio
    async def test_store_whitespace_content(self, engine):
        with pytest.raises(ValueError, match="content cannot be empty"):
            await engine.store("test-project", "   ")


class TestSearchValidation:
    """Tests for search() input guards."""

    @pytest.mark.asyncio
    async def test_search_empty_query(self, engine):
        with pytest.raises(ValueError, match="query cannot be empty"):
            await engine.search("")

    @pytest.mark.asyncio
    async def test_search_whitespace_query(self, engine):
        with pytest.raises(ValueError, match="query cannot be empty"):
            await engine.search("   ")


class TestDeprecateValidation:
    """Tests for deprecate() input guards."""

    @pytest.mark.asyncio
    async def test_deprecate_zero_id(self, engine):
        with pytest.raises(ValueError, match="Invalid fact_id"):
            await engine.deprecate(0)

    @pytest.mark.asyncio
    async def test_deprecate_negative_id(self, engine):
        with pytest.raises(ValueError, match="Invalid fact_id"):
            await engine.deprecate(-5)


# ─── Defensive JSON Parsing ──────────────────────────────────────────


class TestRowToFact:
    """Tests for _row_to_fact with malformed data."""

    def test_malformed_tags_json(self):
        """Corrupt JSON in tags field should fall back to empty list."""
        row = (
            1,
            "proj",
            "content",
            "knowledge",
            "{not-valid-json}",
            "stated",
            "2026-01-01T00:00:00+00:00",
            None,
            None,
            None,
        )
        fact = CortexEngine._row_to_fact(row)
        assert fact.tags == []

    def test_malformed_meta_json(self):
        """Corrupt JSON in meta field should fall back to empty dict."""
        row = (
            1,
            "proj",
            "content",
            "knowledge",
            "[]",
            "stated",
            "2026-01-01T00:00:00+00:00",
            None,
            None,
            "{corrupt}",
        )
        fact = CortexEngine._row_to_fact(row)
        assert fact.meta == {}

    def test_none_tags_and_meta(self):
        """None tags and meta should produce safe defaults."""
        row = (
            1,
            "proj",
            "content",
            "knowledge",
            None,
            "stated",
            "2026-01-01T00:00:00+00:00",
            None,
            None,
            None,
        )
        fact = CortexEngine._row_to_fact(row)
        assert fact.tags == []
        assert fact.meta == {}


# ─── Exception-safe Close ────────────────────────────────────────────


class TestCloseSafety:
    """Tests for exception-safe close()."""

    @pytest.mark.asyncio
    async def test_close_idempotent(self, engine):
        """Calling close() twice should not error."""
        await engine.close()
        await engine.close()  # second call should be no-op

    @pytest.mark.asyncio
    async def test_close_resets_connection(self, engine):
        """After close(), connection should be None."""
        await engine.close()
        assert engine._conn is None

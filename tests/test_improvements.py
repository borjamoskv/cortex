"""
Tests for CORTEX v4.0 improvements.

Tests cover: store_many, update, search filters, recall pagination,
export formats, async client, metrics, and migrations.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio

from cortex.engine import CortexEngine, Fact
from cortex.export import export_facts
from cortex.metrics import MetricsRegistry
from cortex.migrations import (
    ensure_migration_table,
    get_current_version,
    run_migrations,
)
import sqlite_vec


@pytest_asyncio.fixture
async def engine(tmp_path):
    """Create a fresh engine for each test."""
    db = tmp_path / "test.db"
    eng = CortexEngine(str(db), auto_embed=False)
    await eng.init_db()
    yield eng
    await eng.close()


@pytest_asyncio.fixture
async def populated_engine(engine):
    """Engine with some test facts."""
    await engine.store("proj-a", "Python is great", fact_type="knowledge", tags=["python", "lang"])
    await engine.store("proj-a", "TypeScript is typed", fact_type="knowledge", tags=["typescript", "lang"])
    await engine.store("proj-a", "Use pytest for testing", fact_type="decision", tags=["python", "testing"])
    await engine.store("proj-b", "Deploy on Fridays is risky", fact_type="mistake", tags=["deploy", "ops"])
    await engine.store("proj-b", "WAL mode is faster", fact_type="knowledge", tags=["sqlite", "perf"])
    return engine


# ─── store_many Tests ─────────────────────────────────────────────────


class TestStoreMany:
    @pytest.mark.asyncio
    async def test_batch_store_returns_ids(self, engine):
        facts = [
            {"project": "p1", "content": "Fact one"},
            {"project": "p1", "content": "Fact two"},
            {"project": "p1", "content": "Fact three"},
        ]
        ids = await engine.store_many(facts)
        assert len(ids) == 3
        assert all(isinstance(i, int) for i in ids)
        assert len(set(ids)) == 3  # All unique

    @pytest.mark.asyncio
    async def test_batch_store_empty_raises(self, engine):
        with pytest.raises(ValueError, match="empty"):
            await engine.store_many([])

    @pytest.mark.asyncio
    async def test_batch_store_missing_project_raises(self, engine):
        with pytest.raises(ValueError, match="project"):
            await engine.store_many([{"content": "no project"}])

    @pytest.mark.asyncio
    async def test_batch_store_missing_content_raises(self, engine):
        with pytest.raises(ValueError, match="content"):
            await engine.store_many([{"project": "p"}])

    @pytest.mark.asyncio
    async def test_batch_store_with_optional_fields(self, engine):
        facts = [
            {
                "project": "p1",
                "content": "Tagged fact",
                "fact_type": "decision",
                "tags": ["important"],
                "confidence": "inferred",
                "meta": {"key": "value"},
            }
        ]
        ids = await engine.store_many(facts)
        assert len(ids) == 1
        recalled = await engine.recall("p1")
        assert len(recalled) == 1
        assert recalled[0].fact_type == "decision"
        assert "important" in recalled[0].tags

    @pytest.mark.asyncio
    async def test_batch_store_is_atomic(self, engine):
        """All facts should be visible after batch store."""
        facts = [
            {"project": "batch", "content": f"Fact {i}"}
            for i in range(10)
        ]
        ids = await engine.store_many(facts)
        assert len(ids) == 10
        recalled = await engine.recall("batch")
        assert len(recalled) == 10

    @pytest.mark.asyncio
    async def test_batch_store_rollback_on_validation_error(self, engine):
        """Insert 2 valid facts then 1 invalid (empty project) mid-batch.

        Verifies that the ValueError inside the `with conn:` block triggers
        a full ROLLBACK — zero partial commits should survive.
        """
        facts = [
            {"project": "rollback_test", "content": "Fact 0"},
            {"project": "rollback_test", "content": "Fact 1"},
            {"project": "",              "content": "Bad fact"},  # triggers ValueError
            {"project": "rollback_test", "content": "Fact 3"},
        ]

        with pytest.raises(ValueError, match="project"):
            await engine.store_many(facts)

        # Critical assertion: zero facts should persist after rollback
        recalled = await engine.recall("rollback_test")
        assert len(recalled) == 0, (
            f"Expected 0 facts after rollback, got {len(recalled)}"
        )

    def test_database_transaction_error_exists(self):
        """Verify DatabaseTransactionError is importable and properly typed."""
        from cortex.exceptions import DatabaseTransactionError, CortexError

        assert issubclass(DatabaseTransactionError, CortexError)
        assert issubclass(DatabaseTransactionError, Exception)

        err = DatabaseTransactionError("test error")
        assert str(err) == "test error"


# ─── update Tests ─────────────────────────────────────────────────────


class TestUpdate:
    @pytest.mark.asyncio
    async def test_update_content(self, engine):
        original_id = await engine.store("p1", "Original content")
        new_id = await engine.update(original_id, content="Updated content")
        assert new_id != original_id

        facts = await engine.recall("p1")
        assert len(facts) == 1
        assert facts[0].content == "Updated content"
        assert facts[0].id == new_id

    @pytest.mark.asyncio
    async def test_update_tags(self, engine):
        original_id = await engine.store("p1", "Some fact", tags=["old"])
        new_id = await engine.update(original_id, tags=["new", "shiny"])

        facts = await engine.recall("p1")
        assert facts[0].tags == ["new", "shiny"]

    @pytest.mark.asyncio
    async def test_update_preserves_history(self, engine):
        original_id = await engine.store("p1", "V1")
        await engine.update(original_id, content="V2")

        # History should have both versions
        history = await engine.history("p1")
        assert len(history) >= 2

    @pytest.mark.asyncio
    async def test_update_preserves_meta_lineage(self, engine):
        original_id = await engine.store("p1", "Original", meta={"source": "test"})
        new_id = await engine.update(original_id, content="Updated")

        facts = await engine.recall("p1")
        assert facts[0].meta.get("previous_fact_id") == original_id

    @pytest.mark.asyncio
    async def test_update_invalid_id_raises(self, engine):
        with pytest.raises(ValueError):
            await engine.update(0)

    @pytest.mark.asyncio
    async def test_update_nonexistent_raises(self, engine):
        with pytest.raises(ValueError, match="not found"):
            await engine.update(9999)

    @pytest.mark.asyncio
    async def test_update_keeps_unchanged_fields(self, engine):
        original_id = await engine.store(
            "p1", "Content", fact_type="decision", tags=["tag1"], source="test",
        )
        new_id = await engine.update(original_id, tags=["tag2"])

        facts = await engine.recall("p1")
        assert facts[0].content == "Content"
        assert facts[0].fact_type == "decision"
        assert facts[0].tags == ["tag2"]


# ─── Search Filters Tests ────────────────────────────────────────────


class TestSearchFilters:
    @pytest.mark.asyncio
    async def test_search_by_tag_filter(self, populated_engine):
        results = await populated_engine.search("programming", tags=["python"])
        for r in results:
            conn = populated_engine._get_conn()
            cursor = await conn.execute(
                "SELECT tags FROM facts WHERE id = ?", (r.fact_id,)
            )
            fact = await cursor.fetchone()
            if fact:
                tags = json.loads(fact[0])
                assert "python" in tags

    @pytest.mark.asyncio
    async def test_search_by_fact_type_filter(self, populated_engine):
        results = await populated_engine.search("testing", fact_type="decision")
        for r in results:
            assert r.fact_type == "decision"

    @pytest.mark.asyncio
    async def test_search_combined_filters(self, populated_engine):
        results = await populated_engine.search(
            "language", tags=["lang"], fact_type="knowledge"
        )
        for r in results:
            assert r.fact_type == "knowledge"


# ─── Recall Pagination Tests ─────────────────────────────────────────


class TestRecallPagination:
    @pytest.mark.asyncio
    async def test_recall_all(self, populated_engine):
        facts = await populated_engine.recall("proj-a")
        assert len(facts) == 3

    @pytest.mark.asyncio
    async def test_recall_with_limit(self, populated_engine):
        facts = await populated_engine.recall("proj-a", limit=2)
        assert len(facts) == 2

    @pytest.mark.asyncio
    async def test_recall_with_offset(self, populated_engine):
        all_facts = await populated_engine.recall("proj-a")
        page2 = await populated_engine.recall("proj-a", limit=2, offset=2)
        assert len(page2) == 1
        assert page2[0].id == all_facts[2].id

    @pytest.mark.asyncio
    async def test_recall_pagination_consistency(self, populated_engine):
        page1 = await populated_engine.recall("proj-a", limit=2, offset=0)
        page2 = await populated_engine.recall("proj-a", limit=2, offset=2)
        all_facts = await populated_engine.recall("proj-a")
        paginated = page1 + page2
        assert len(paginated) == len(all_facts)

    @pytest.mark.asyncio
    async def test_recall_empty_project(self, engine):
        facts = await engine.recall("nonexistent")
        assert facts == []

    @pytest.mark.asyncio
    async def test_recall_limit_none_returns_all(self, populated_engine):
        all_facts = await populated_engine.recall("proj-a", limit=None)
        assert len(all_facts) == 3


# ─── Export Tests ─────────────────────────────────────────────────────


class TestExport:
    @pytest.mark.asyncio
    async def test_export_json(self, populated_engine):
        facts = await populated_engine.recall("proj-a")
        result = export_facts(facts, "json")
        parsed = json.loads(result)
        assert len(parsed) == 3
        assert all("content" in f for f in parsed)

    @pytest.mark.asyncio
    async def test_export_csv(self, populated_engine):
        facts = await populated_engine.recall("proj-a")
        result = export_facts(facts, "csv")
        lines = result.strip().split("\n")
        assert len(lines) == 4  # header + 3 facts
        assert "id" in lines[0]
        assert "content" in lines[0]

    @pytest.mark.asyncio
    async def test_export_jsonl(self, populated_engine):
        facts = await populated_engine.recall("proj-a")
        result = export_facts(facts, "jsonl")
        lines = result.strip().split("\n")
        assert len(lines) == 3
        for line in lines:
            parsed = json.loads(line)
            assert "content" in parsed

    def test_export_empty(self):
        result = export_facts([], "json")
        assert json.loads(result) == []

    def test_export_csv_empty(self):
        result = export_facts([], "csv")
        assert result == ""

    def test_export_invalid_format(self):
        with pytest.raises(ValueError, match="Unsupported"):
            export_facts([], "xml")


# ─── Metrics Tests ────────────────────────────────────────────────────


class TestMetrics:
    def test_counter_increment(self):
        reg = MetricsRegistry()
        reg.inc("test_counter")
        reg.inc("test_counter")
        output = reg.to_prometheus()
        assert "test_counter 2" in output

    def test_counter_with_labels(self):
        reg = MetricsRegistry()
        reg.inc("requests", {"method": "GET", "status": "200"})
        output = reg.to_prometheus()
        assert 'requests{method="GET",status="200"} 1' in output

    def test_gauge(self):
        reg = MetricsRegistry()
        reg.set_gauge("active_facts", 42.0)
        output = reg.to_prometheus()
        assert "active_facts 42.00" in output

    def test_histogram(self):
        reg = MetricsRegistry()
        reg.observe("duration", 0.1)
        reg.observe("duration", 0.2)
        output = reg.to_prometheus()
        assert "duration_count 2" in output
        assert "duration_sum" in output

    def test_prometheus_format(self):
        reg = MetricsRegistry()
        reg.inc("cortex_requests")
        output = reg.to_prometheus()
        assert "# TYPE cortex_requests counter" in output

    def test_reset(self):
        reg = MetricsRegistry()
        reg.inc("counter")
        reg.set_gauge("gauge", 1.0)
        reg.reset()
        output = reg.to_prometheus()
        assert "counter" not in output


# ─── Migration Tests ─────────────────────────────────────────────────


class TestMigrations:
    def test_fresh_db_at_version_zero(self, tmp_path):
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        assert get_current_version(conn) == 0
        conn.close()

    def test_migrations_applied(self, tmp_path):
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        try:
            if hasattr(conn, "enable_load_extension"):
                conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            if hasattr(conn, "enable_load_extension"):
                conn.enable_load_extension(False)
        except (AttributeError, OSError):
            pass
        # Create minimal facts table for migrations
        conn.execute("""
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY,
                project TEXT, content TEXT, fact_type TEXT,
                tags TEXT, confidence TEXT, valid_from TEXT,
                valid_until TEXT, source TEXT, meta TEXT,
                created_at TEXT
            )
        """)
        conn.commit()

        applied = run_migrations(conn)
        assert applied >= 1
        assert get_current_version(conn) >= 1
        conn.close()

    def test_migrations_idempotent(self, tmp_path):
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        try:
            if hasattr(conn, "enable_load_extension"):
                conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            if hasattr(conn, "enable_load_extension"):
                conn.enable_load_extension(False)
        except (AttributeError, OSError):
            pass

        conn.execute("""
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY,
                project TEXT, content TEXT, fact_type TEXT,
                tags TEXT, confidence TEXT, valid_from TEXT,
                valid_until TEXT, source TEXT, meta TEXT,
                created_at TEXT
            )
        """)
        conn.commit()

        first = run_migrations(conn)
        second = run_migrations(conn)
        assert first >= 1
        assert second == 0  # No new migrations
        conn.close()

    def test_version_table_created(self, tmp_path):
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        ensure_migration_table(conn)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        ).fetchall()
        assert len(tables) == 1
        conn.close()


# ─── Client Tests (sync) ─────────────────────────────────────────────


class TestCortexClient:
    """Test client methods without live server (mocked requests)."""

    def test_client_import(self):
        from cortex.client import CortexClient, CortexError, Fact
        assert CortexClient is not None
        assert CortexError is not None

    def test_async_client_import(self):
        from cortex.async_client import AsyncCortexClient
        assert AsyncCortexClient is not None

    def test_client_context_manager(self):
        from cortex.client import CortexClient
        with CortexClient("http://fake:9999") as client:
            assert client is not None

    def test_client_headers(self):
        from cortex.client import CortexClient
        client = CortexClient("http://fake:9999", api_key="test-key")
        headers = client._headers()
        assert headers["Authorization"] == "Bearer test-key"
        client.close()

    def test_client_no_key(self):
        from cortex.client import CortexClient
        with patch.dict(os.environ, {}, clear=True):
            client = CortexClient("http://fake:9999", api_key=None)
            headers = client._headers()
            assert "Authorization" not in headers
            client.close()

    def test_cortex_error(self):
        from cortex.client import CortexError
        err = CortexError(404, "Not found")
        assert err.status_code == 404
        assert err.detail == "Not found"
        assert "404" in str(err)

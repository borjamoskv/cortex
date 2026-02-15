"""
CORTEX v4.0 — Core Engine Tests.

Tests for store, search, recall, history, deprecation, and stats.
"""

import json
import os
import tempfile

import pytest

from cortex.engine import CortexEngine


@pytest.fixture
def engine():
    """Create a temporary CORTEX engine for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    eng = CortexEngine(db_path=db_path, auto_embed=False)
    eng.init_db()
    yield eng
    eng.close()
    os.unlink(db_path)


@pytest.fixture
def engine_with_data(engine):
    """Engine preloaded with test data."""
    engine.store("naroa-web", "Uses vanilla JS, no framework", fact_type="decision",
                 tags=["js", "architecture"])
    engine.store("naroa-web", "Industrial Noir aesthetic with YInMn Blue",
                 fact_type="decision", tags=["design", "aesthetic"])
    engine.store("naroa-web", "Gallery uses chromatic aberration on hover",
                 fact_type="knowledge", tags=["gallery", "effects"])
    engine.store("live-notch", "Native SwiftUI app, not Electron",
                 fact_type="decision", tags=["swift", "architecture"])
    engine.store("moskvbot", "Multi-channel bot using Kimi K2.5 API",
                 fact_type="knowledge", tags=["bot", "api"])
    return engine


class TestInit:
    def test_init_creates_tables(self, engine):
        conn = engine._get_conn()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {t[0] for t in tables}
        assert "facts" in table_names
        assert "sessions" in table_names
        assert "transactions" in table_names
        assert "cortex_meta" in table_names

    def test_init_sets_metadata(self, engine):
        conn = engine._get_conn()
        version = conn.execute(
            "SELECT value FROM cortex_meta WHERE key='schema_version'"
        ).fetchone()
        assert version[0] == "4.0.0"

    def test_init_idempotent(self, engine):
        """Calling init_db twice should not error."""
        engine.init_db()
        engine.init_db()


class TestStore:
    def test_store_returns_id(self, engine):
        fact_id = engine.store("test-project", "Test fact")
        assert fact_id > 0

    def test_store_increments_id(self, engine):
        id1 = engine.store("test", "Fact 1")
        id2 = engine.store("test", "Fact 2")
        assert id2 > id1

    def test_store_with_tags(self, engine):
        engine.store("test", "Tagged fact", tags=["tag1", "tag2"])
        conn = engine._get_conn()
        row = conn.execute("SELECT tags FROM facts WHERE id=1").fetchone()
        tags = json.loads(row[0])
        assert tags == ["tag1", "tag2"]

    def test_store_creates_transaction(self, engine):
        engine.store("test", "Audited fact")
        conn = engine._get_conn()
        tx = conn.execute("SELECT * FROM transactions").fetchone()
        assert tx is not None
        assert tx[1] == "test"  # project
        assert tx[2] == "store"  # action

    def test_transaction_hash_chain(self, engine):
        engine.store("test", "Fact 1")
        engine.store("test", "Fact 2")
        conn = engine._get_conn()
        txs = conn.execute(
            "SELECT prev_hash, hash FROM transactions ORDER BY id"
        ).fetchall()
        assert txs[0][0] == "GENESIS"
        assert txs[1][0] == txs[0][1]  # Chain integrity


class TestRecall:
    def test_recall_returns_active_facts(self, engine_with_data):
        facts = engine_with_data.recall("naroa-web")
        assert len(facts) == 3

    def test_recall_scoped_to_project(self, engine_with_data):
        facts = engine_with_data.recall("live-notch")
        assert len(facts) == 1
        assert "SwiftUI" in facts[0].content

    def test_recall_empty_project(self, engine_with_data):
        facts = engine_with_data.recall("nonexistent")
        assert len(facts) == 0


class TestDeprecate:
    def test_deprecate_marks_valid_until(self, engine_with_data):
        result = engine_with_data.deprecate(1, reason="Outdated")
        assert result is True

        facts = engine_with_data.recall("naroa-web")
        active_ids = {f.id for f in facts}
        assert 1 not in active_ids

    def test_deprecate_nonexistent(self, engine):
        result = engine.deprecate(999)
        assert result is False

    def test_deprecated_fact_still_in_history(self, engine_with_data):
        engine_with_data.deprecate(1)

        # All history should include it
        all_facts = engine_with_data.history("naroa-web")
        all_ids = {f.id for f in all_facts}
        assert 1 in all_ids


class TestHistory:
    def test_history_returns_all_facts(self, engine_with_data):
        facts = engine_with_data.history("naroa-web")
        assert len(facts) == 3

    def test_history_includes_deprecated(self, engine_with_data):
        engine_with_data.deprecate(1)
        facts = engine_with_data.history("naroa-web")
        assert len(facts) == 3  # Still includes deprecated


class TestStats:
    def test_stats_correct(self, engine_with_data):
        s = engine_with_data.stats()
        assert s["total_facts"] == 5
        assert s["active_facts"] == 5
        assert s["deprecated_facts"] == 0
        assert s["project_count"] == 3
        assert "naroa-web" in s["projects"]

    def test_stats_after_deprecate(self, engine_with_data):
        engine_with_data.deprecate(1)
        s = engine_with_data.stats()
        assert s["active_facts"] == 4
        assert s["deprecated_facts"] == 1


class TestTextSearch:
    def test_text_search_finds_match(self, engine_with_data):
        # Text search (since auto_embed=False)
        results = engine_with_data.search("vanilla JS")
        assert len(results) > 0
        assert "vanilla JS" in results[0].content

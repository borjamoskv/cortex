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
async def engine():
    """Create a temporary CORTEX engine for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    eng = CortexEngine(db_path=db_path, auto_embed=False)
    await eng.init_db()
    yield eng
    await eng.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
async def engine_with_data(engine):
    """Engine preloaded with test data."""
    await engine.store(
        "naroa-web",
        "Uses vanilla JS, no framework",
        fact_type="decision",
        tags=["js", "architecture"],
    )
    await engine.store(
        "naroa-web",
        "Industrial Noir aesthetic with YInMn Blue",
        fact_type="decision",
        tags=["design", "aesthetic"],
    )
    await engine.store(
        "naroa-web",
        "Gallery uses chromatic aberration on hover",
        fact_type="knowledge",
        tags=["gallery", "effects"],
    )
    await engine.store(
        "live-notch",
        "Native SwiftUI app, not Electron",
        fact_type="decision",
        tags=["swift", "architecture"],
    )
    await engine.store(
        "moskvbot",
        "Multi-channel bot using Kimi K2.5 API",
        fact_type="knowledge",
        tags=["bot", "api"],
    )
    return engine


@pytest.mark.asyncio
class TestInit:
    async def test_init_creates_tables(self, engine):
        conn = await engine.get_conn()
        async with conn.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
            tables = await cursor.fetchall()
        table_names = {t[0] for t in tables}
        assert "facts" in table_names
        assert "sessions" in table_names
        assert "transactions" in table_names
        assert "cortex_meta" in table_names

    async def test_init_sets_metadata(self, engine):
        conn = await engine.get_conn()
        async with conn.execute(
            "SELECT value FROM cortex_meta WHERE key='schema_version'"
        ) as cursor:
            version = await cursor.fetchone()
        assert version[0] == "4.0.0"

    async def test_init_idempotent(self, engine):
        """Calling init_db twice should not error."""
        await engine.init_db()
        await engine.init_db()


@pytest.mark.asyncio
class TestStore:
    async def test_store_returns_id(self, engine):
        fact_id = await engine.store("test-project", "Test fact")
        assert fact_id > 0

    async def test_store_increments_id(self, engine):
        id1 = await engine.store("test", "Fact 1")
        id2 = await engine.store("test", "Fact 2")
        assert id2 > id1

    async def test_store_with_tags(self, engine):
        await engine.store("test", "Tagged fact", tags=["tag1", "tag2"])
        conn = await engine.get_conn()
        async with conn.execute("SELECT tags FROM facts WHERE id=1") as cursor:
            row = await cursor.fetchone()
        tags = json.loads(row[0])
        assert tags == ["tag1", "tag2"]

    async def test_store_creates_transaction(self, engine):
        await engine.store("test", "Audited fact")
        conn = await engine.get_conn()
        async with conn.execute("SELECT * FROM transactions") as cursor:
            tx = await cursor.fetchone()
        assert tx is not None
        assert tx[1] == "test"  # project
        assert tx[2] == "store"  # action

    async def test_transaction_hash_chain(self, engine):
        await engine.store("test", "Fact 1")
        await engine.store("test", "Fact 2")
        conn = await engine.get_conn()
        async with conn.execute("SELECT prev_hash, hash FROM transactions ORDER BY id") as cursor:
            txs = await cursor.fetchall()
        assert txs[0][0] == "GENESIS"
        assert txs[1][0] == txs[0][1]  # Chain integrity


@pytest.mark.asyncio
class TestRecall:
    async def test_recall_returns_active_facts(self, engine_with_data):
        facts = await engine_with_data.recall("naroa-web")
        assert len(facts) == 3

    async def test_recall_scoped_to_project(self, engine_with_data):
        facts = await engine_with_data.recall("live-notch")
        assert len(facts) == 1
        assert "SwiftUI" in facts[0].content

    async def test_recall_empty_project(self, engine_with_data):
        facts = await engine_with_data.recall("nonexistent")
        assert len(facts) == 0


@pytest.mark.asyncio
class TestDeprecate:
    async def test_deprecate_marks_valid_until(self, engine_with_data):
        result = await engine_with_data.deprecate(1, reason="Outdated")
        assert result is True

        facts = await engine_with_data.recall("naroa-web")
        active_ids = {f.id for f in facts}
        assert 1 not in active_ids

    async def test_deprecate_nonexistent(self, engine):
        result = await engine.deprecate(999)
        assert result is False

    async def test_deprecated_fact_still_in_history(self, engine_with_data):
        await engine_with_data.deprecate(1)

        # All history should include it
        all_facts = await engine_with_data.history("naroa-web")
        all_ids = {f.id for f in all_facts}
        assert 1 in all_ids


@pytest.mark.asyncio
class TestHistory:
    async def test_history_returns_all_facts(self, engine_with_data):
        facts = await engine_with_data.history("naroa-web")
        assert len(facts) == 3

    async def test_history_includes_deprecated(self, engine_with_data):
        await engine_with_data.deprecate(1)
        facts = await engine_with_data.history("naroa-web")
        assert len(facts) == 3  # Still includes deprecated


@pytest.mark.asyncio
class TestStats:
    async def test_stats_correct(self, engine_with_data):
        s = await engine_with_data.stats()
        assert s["total_facts"] == 5
        assert s["active_facts"] == 5
        assert s["deprecated_facts"] == 0
        assert s["project_count"] == 3
        assert "naroa-web" in s["projects"]

    async def test_stats_after_deprecate(self, engine_with_data):
        await engine_with_data.deprecate(1)
        s = await engine_with_data.stats()
        assert s["active_facts"] == 4
        assert s["deprecated_facts"] == 1


@pytest.mark.asyncio
class TestTextSearch:
    async def test_text_search_finds_match(self, engine_with_data):
        # Text search (since auto_embed=False)
        results = await engine_with_data.search("vanilla JS")
        assert len(results) > 0
        assert "vanilla JS" in results[0].content

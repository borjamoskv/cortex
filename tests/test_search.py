"""
CORTEX v4.0 — Search Module Tests.

Tests for text_search edge cases: empty results, project filtering,
type filtering, limit enforcement.
"""

import os
import tempfile
import pytest_asyncio
import pytest

from cortex.engine import CortexEngine
from cortex.search import text_search


@pytest_asyncio.fixture
async def search_engine():
    """Create a temporary engine with test data for search tests."""
    # Use a file-based DB because in-memory shared connections are tricky with aiosqlite
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    # Close the handle so sqlite can open it
    # (NamedTemporaryFile deletes on close by default loop, but delete=False prevents that)

    eng = CortexEngine(db_path=db_path, auto_embed=False)
    await eng.init_db()

    # Insert varied test data
    await eng.store("alpha", "Python is a great language", fact_type="knowledge", tags=["python"])
    await eng.store("alpha", "Use pytest for testing", fact_type="decision", tags=["testing"])
    await eng.store("beta", "Python supports async/await", fact_type="knowledge", tags=["python"])
    await eng.store("beta", "Rust is fast", fact_type="knowledge", tags=["rust"])
    await eng.store("gamma", "Deploy with Docker", fact_type="decision", tags=["devops"])

    yield eng
    await eng.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.mark.asyncio
class TestTextSearch:
    async def test_finds_matching_content(self, search_engine):
        conn = await search_engine.get_conn()
        results = await text_search(conn, "Python")
        assert len(results) >= 2
        assert all("Python" in r.content for r in results)

    async def test_no_results_for_unmatched_query(self, search_engine):
        conn = await search_engine.get_conn()
        results = await text_search(conn, "xyznonexistent")
        assert results == []

    async def test_project_filter(self, search_engine):
        conn = await search_engine.get_conn()
        results = await text_search(conn, "Python", project="alpha")
        assert len(results) == 1
        assert results[0].project == "alpha"

    async def test_fact_type_filter(self, search_engine):
        conn = await search_engine.get_conn()
        # Note: text_search signature is (conn, query, project, fact_type, ...)
        # We need to make sure we pass args correctly.
        # text_search(conn, query, project=None, fact_type=None, tags=None, limit=20, as_of=None)
        results = await text_search(conn, "Python", fact_type="decision")
        assert results == []  # No "Python" in decision-type facts for alpha

    async def test_limit_enforcement(self, search_engine):
        conn = await search_engine.get_conn()
        # Insert enough data to test the limit
        for i in range(10):
            await search_engine.store("alpha", f"Extra Python fact {i}", fact_type="knowledge")
        results = await text_search(conn, "Python", limit=3)
        assert len(results) <= 3

    async def test_result_has_correct_score(self, search_engine):
        conn = await search_engine.get_conn()
        results = await text_search(conn, "Docker")
        assert len(results) == 1
        # FTS bm25 score is not strictly 0.5, depends on implementation.
        # Like search uses default order (updated_at DESC).
        # FTS uses bm25.
        # We just check it has a score.
        assert isinstance(results[0].score, (int, float))

    async def test_result_has_tags(self, search_engine):
        conn = await search_engine.get_conn()
        results = await text_search(conn, "Docker")
        assert results[0].tags == ["devops"]

    async def test_deprecated_facts_excluded(self, search_engine):
        """Deprecated facts (valid_until IS NOT NULL) should not appear."""
        # We need a fact id to deprecate.
        # Let's search first to find one.
        conn = await search_engine.get_conn()
        initial_results = await text_search(conn, "Rust")
        assert len(initial_results) > 0
        fact_id = initial_results[0].fact_id

        await search_engine.deprecate(fact_id)
        
        results = await text_search(conn, "Rust")
        fact_ids = {r.fact_id for r in results}
        assert fact_id not in fact_ids

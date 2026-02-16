"""
CORTEX v4.0 — Sync Search Module Tests.

Tests for semantic_search_sync, text_search_sync, hybrid_search_sync,
and the CortexEngine.search_sync() integration method.
"""

import os
import tempfile

import pytest

from cortex.engine import CortexEngine
from cortex.search_sync import (
    SyncSearchResult,
    hybrid_search_sync,
    semantic_search_sync,
    text_search_sync,
)


@pytest.fixture
def search_engine():
    """Create a temporary engine with test data and embeddings."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    eng = CortexEngine(db_path=db_path, auto_embed=True)
    eng.init_db_sync()

    # Insert test data with embeddings via store_sync
    eng.store_sync("alpha", "Python is great for machine learning", fact_type="knowledge")
    eng.store_sync("alpha", "Use pytest for testing Python code", fact_type="decision")
    eng.store_sync(
        "beta", "Rust offers memory safety without garbage collection", fact_type="knowledge"
    )
    eng.store_sync("beta", "Docker containers simplify deployment", fact_type="knowledge")
    eng.store_sync("gamma", "Neural networks require training data", fact_type="knowledge")

    yield eng
    eng.close_sync()
    os.unlink(db_path)


@pytest.fixture
def no_vec_engine():
    """Engine without vector support for text-only fallback tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    eng = CortexEngine(db_path=db_path, auto_embed=False)
    eng.init_db_sync()

    eng.store_sync("alpha", "Python is great for machine learning", fact_type="knowledge")
    eng.store_sync("alpha", "Use pytest for testing", fact_type="decision")

    yield eng
    eng.close_sync()
    os.unlink(db_path)


# ── Text Search Sync ──────────────────────────────────────


class TestTextSearchSync:
    def test_finds_matching_content(self, search_engine):
        conn = search_engine._get_sync_conn()
        results = text_search_sync(conn, "Python")
        assert len(results) >= 2
        assert all("Python" in r.content for r in results)

    def test_no_results_for_unmatched(self, search_engine):
        conn = search_engine._get_sync_conn()
        results = text_search_sync(conn, "xyznonexistent")
        assert results == []

    def test_project_filter(self, search_engine):
        conn = search_engine._get_sync_conn()
        results = text_search_sync(conn, "Python", project="alpha")
        assert len(results) >= 1
        assert all(r.project == "alpha" for r in results)

    def test_limit_enforcement(self, search_engine):
        conn = search_engine._get_sync_conn()
        results = text_search_sync(conn, "Python", limit=1)
        assert len(results) <= 1

    def test_result_is_sync_search_result(self, search_engine):
        conn = search_engine._get_sync_conn()
        results = text_search_sync(conn, "Docker")
        assert len(results) == 1
        assert isinstance(results[0], SyncSearchResult)
        assert results[0].score != 0.0  # Should be non-zero

    def test_to_dict(self, search_engine):
        conn = search_engine._get_sync_conn()
        results = text_search_sync(conn, "Docker")
        d = results[0].to_dict()
        assert "content" in d
        assert "score" in d
        assert d["project"] == "beta"


# ── Semantic Search Sync ──────────────────────────────────


class TestSemanticSearchSync:
    def test_finds_semantically_similar(self, search_engine):
        """Vector search should find 'machine learning' when querying 'AI'."""
        if not search_engine._vec_available:
            pytest.skip("sqlite-vec not available")

        conn = search_engine._get_sync_conn()
        embedding = search_engine._get_embedder().embed("artificial intelligence")
        results = semantic_search_sync(conn, embedding, top_k=3)
        assert len(results) > 0
        # Should rank ML/neural content higher than Docker
        contents = [r.content for r in results]
        assert any("machine learning" in c or "Neural" in c for c in contents)

    def test_returns_real_scores(self, search_engine):
        """Vector scores should be real cosine similarities, not flat 1.0."""
        if not search_engine._vec_available:
            pytest.skip("sqlite-vec not available")

        conn = search_engine._get_sync_conn()
        embedding = search_engine._get_embedder().embed("Python programming")
        results = semantic_search_sync(conn, embedding, top_k=3)
        for r in results:
            assert 0.0 < r.score <= 1.0
            assert r.score != 1.0  # Should be real similarity, not flat

    def test_project_filter_semantic(self, search_engine):
        if not search_engine._vec_available:
            pytest.skip("sqlite-vec not available")

        conn = search_engine._get_sync_conn()
        embedding = search_engine._get_embedder().embed("Python")
        results = semantic_search_sync(conn, embedding, top_k=5, project="beta")
        assert all(r.project == "beta" for r in results)


# ── Hybrid Search Sync ────────────────────────────────────


class TestHybridSearchSync:
    def test_combines_both_methods(self, search_engine):
        if not search_engine._vec_available:
            pytest.skip("sqlite-vec not available")

        conn = search_engine._get_sync_conn()
        embedding = search_engine._get_embedder().embed("Python programming language")
        results = hybrid_search_sync(conn, "Python", embedding, top_k=5)
        assert len(results) > 0
        # RRF scores should be small positive values
        assert all(r.score > 0 for r in results)

    def test_project_filter_hybrid(self, search_engine):
        if not search_engine._vec_available:
            pytest.skip("sqlite-vec not available")

        conn = search_engine._get_sync_conn()
        embedding = search_engine._get_embedder().embed("Python")
        results = hybrid_search_sync(
            conn,
            "Python",
            embedding,
            top_k=5,
            project="alpha",
        )
        assert all(r.project == "alpha" for r in results)


# ── Engine Integration ────────────────────────────────────


class TestEngineSearchSync:
    def test_search_sync_returns_results(self, search_engine):
        results = search_engine.search_sync("Python programming", top_k=3)
        assert len(results) > 0

    def test_search_sync_project_filter(self, search_engine):
        results = search_engine.search_sync("Python", project="alpha", top_k=3)
        assert all(r.project == "alpha" for r in results)

    def test_search_sync_empty_query_raises(self, search_engine):
        with pytest.raises(ValueError):
            search_engine.search_sync("")

    def test_search_sync_no_vec_fallback(self, no_vec_engine):
        """Without sqlite-vec, search_sync should fall back to text search."""
        results = no_vec_engine.search_sync("Python", top_k=3)
        assert len(results) > 0
        assert all("Python" in r.content for r in results)

    def test_hybrid_search_sync_integration(self, search_engine):
        if not search_engine._vec_available:
            pytest.skip("sqlite-vec not available")

        results = search_engine.hybrid_search_sync("Python", top_k=5)
        assert len(results) > 0
        # Should have RRF scores
        assert all(r.score > 0 for r in results)

"""
CORTEX v4.0 — Context Engine Tests.

Tests for signal collection, inference, confidence scoring,
snapshot persistence, and edge cases.
"""

import os
import tempfile

import pytest

from cortex.context.collector import ContextCollector, _recency_decay
from cortex.context.inference import ContextInference
from cortex.context.signals import InferenceResult, Signal
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
    """Engine preloaded with multi-project data for context testing."""
    # Project A: 5 facts (dominant)
    for i in range(5):
        await engine.store("alpha-project", f"Alpha fact #{i}", fact_type="decision")

    # Project B: 2 facts
    await engine.store("beta-project", "Beta knowledge 1", fact_type="knowledge")
    await engine.store("beta-project", "Beta knowledge 2", fact_type="knowledge")

    # Project C: 1 fact
    await engine.store("gamma-project", "Gamma single fact", fact_type="ghost")

    return engine


# ─── Signal Dataclass Tests ──────────────────────────────────────────


@pytest.mark.asyncio
class TestSignalDataclass:
    async def test_signal_to_dict(self):
        s = Signal(
            source="db:facts",
            signal_type="recent_fact",
            content="Test content",
            project="test-project",
            timestamp="2026-02-20T00:00:00",
            weight=0.8,
        )
        d = s.to_dict()
        assert d["source"] == "db:facts"
        assert d["project"] == "test-project"
        assert d["weight"] == 0.8

    async def test_inference_result_to_dict(self):
        result = InferenceResult(
            active_project="test",
            confidence="C4",
            signals_used=5,
            summary="Test summary",
            top_signals=[],
            projects_ranked=[("test", 3.5), ("other", 1.0)],
        )
        d = result.to_dict()
        assert d["active_project"] == "test"
        assert d["confidence"] == "C4"
        assert len(d["projects_ranked"]) == 2
        assert d["projects_ranked"][0]["project"] == "test"


# ─── Recency Decay Tests ────────────────────────────────────────────


@pytest.mark.asyncio
class TestRecencyDecay:
    async def test_first_rank_is_full_weight(self):
        assert _recency_decay(0, 10) == 1.0

    async def test_last_rank_is_half_weight(self):
        assert _recency_decay(9, 10) == 0.5

    async def test_single_item(self):
        assert _recency_decay(0, 1) == 1.0

    async def test_middle_rank(self):
        # rank 5 of 10: 1.0 - 0.5 * (5/9) ≈ 0.722
        decay = _recency_decay(5, 10)
        assert 0.7 < decay < 0.75


# ─── Collector Tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCollector:
    async def test_collect_recent_facts(self, engine_with_data):
        conn = await engine_with_data.get_conn()
        collector = ContextCollector(
            conn=conn, max_signals=50, git_enabled=False,
            workspace_dir="/nonexistent",
        )
        signals = await collector._collect_recent_facts(limit=10)
        assert len(signals) >= 8  # At least 5 + 2 + 1 facts

        # All should be recent_fact type
        for s in signals:
            assert s.signal_type == "recent_fact"
            assert s.source == "db:facts"

    async def test_collect_active_ghosts_empty(self, engine):
        conn = await engine.get_conn()
        collector = ContextCollector(conn=conn, git_enabled=False)
        ghosts = await collector._collect_active_ghosts()
        assert ghosts == []

    async def test_collect_all_returns_capped(self, engine_with_data):
        conn = await engine_with_data.get_conn()
        collector = ContextCollector(
            conn=conn, max_signals=5, git_enabled=False,
            workspace_dir="/nonexistent",
        )
        signals = await collector.collect_all()
        assert len(signals) <= 5

    async def test_collect_all_sorted_by_weight(self, engine_with_data):
        conn = await engine_with_data.get_conn()
        collector = ContextCollector(
            conn=conn, max_signals=20, git_enabled=False,
            workspace_dir="/nonexistent",
        )
        signals = await collector.collect_all()
        weights = [s.weight for s in signals]
        assert weights == sorted(weights, reverse=True)

    async def test_empty_db_returns_empty(self, engine):
        conn = await engine.get_conn()
        collector = ContextCollector(
            conn=conn, max_signals=20, git_enabled=False,
            workspace_dir="/nonexistent",
        )
        signals = await collector.collect_all()
        # May contain fs/git signals; DB signals should be 0
        db_signals = [s for s in signals if s.source.startswith("db:")]
        assert db_signals == []


# ─── Inference Tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestInference:
    async def test_empty_signals_returns_c1(self):
        inference = ContextInference()
        result = inference.infer([])
        assert result.confidence == "C1"
        assert result.active_project is None
        assert result.signals_used == 0

    async def test_single_project_high_confidence(self):
        signals = [
            Signal("db:facts", "recent_fact", "fact 1", "alpha", "2026-01-01", 0.9),
            Signal("db:facts", "recent_fact", "fact 2", "alpha", "2026-01-01", 0.8),
            Signal("db:facts", "recent_fact", "fact 3", "alpha", "2026-01-01", 0.7),
        ]
        inference = ContextInference()
        result = inference.infer(signals)
        assert result.active_project == "alpha"
        assert result.confidence == "C5"  # No competitor → ratio = inf

    async def test_dominant_project_beats_minor(self):
        signals = [
            Signal("db:facts", "recent_fact", "alpha 1", "alpha", "2026-01-01", 0.9),
            Signal("db:facts", "recent_fact", "alpha 2", "alpha", "2026-01-01", 0.9),
            Signal("db:facts", "recent_fact", "alpha 3", "alpha", "2026-01-01", 0.9),
            Signal("db:facts", "recent_fact", "beta 1", "beta", "2026-01-01", 0.3),
        ]
        inference = ContextInference()
        result = inference.infer(signals)
        assert result.active_project == "alpha"
        assert result.confidence in ("C4", "C5")
        assert result.projects_ranked[0][0] == "alpha"

    async def test_ambiguous_projects_low_confidence(self):
        signals = [
            Signal("db:facts", "recent_fact", "alpha 1", "alpha", "2026-01-01", 0.5),
            Signal("db:facts", "recent_fact", "beta 1", "beta", "2026-01-01", 0.5),
        ]
        inference = ContextInference()
        result = inference.infer(signals)
        # Equal scores → ratio = 1.0 → C1 (below all thresholds except 0.0)
        assert result.confidence in ("C1", "C2")

    async def test_orphan_signals_handled(self):
        signals = [
            Signal("fs:recent", "file_change", "some file", None, "2026-01-01", 0.4),
        ]
        inference = ContextInference()
        result = inference.infer(signals)
        assert result.signals_used == 1
        # No project signals → no ranked projects
        assert result.active_project is None

    async def test_summary_contains_project_name(self):
        signals = [
            Signal("db:facts", "recent_fact", "fact 1", "cortex", "2026-01-01", 0.9),
        ]
        inference = ContextInference()
        result = inference.infer(signals)
        assert "cortex" in result.summary

    async def test_projects_ranked_descending(self):
        signals = [
            Signal("db:facts", "recent_fact", "a", "alpha", "2026-01-01", 0.9),
            Signal("db:facts", "recent_fact", "b", "beta", "2026-01-01", 0.5),
            Signal("db:facts", "recent_fact", "c", "gamma", "2026-01-01", 0.2),
        ]
        inference = ContextInference()
        result = inference.infer(signals)
        scores = [s for _, s in result.projects_ranked]
        assert scores == sorted(scores, reverse=True)


# ─── Snapshot Persistence Tests ──────────────────────────────────────


@pytest.mark.asyncio
class TestSnapshotPersistence:
    async def test_persist_snapshot(self, engine_with_data):
        conn = await engine_with_data.get_conn()

        # Ensure table exists
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS context_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                active_project TEXT,
                confidence TEXT NOT NULL,
                signals_used INTEGER NOT NULL,
                summary TEXT NOT NULL,
                signals_json TEXT,
                projects_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )"""
        )
        await conn.commit()

        collector = ContextCollector(
            conn=conn, max_signals=20, git_enabled=False,
            workspace_dir="/nonexistent",
        )
        signals = await collector.collect_all()

        inference = ContextInference(conn=conn)
        result = await inference.infer_and_persist(signals)

        # Verify it was persisted
        async with conn.execute("SELECT COUNT(*) FROM context_snapshots") as cursor:
            count = (await cursor.fetchone())[0]
        assert count == 1

        # Verify history retrieval
        history = await inference.get_history()
        assert len(history) == 1
        assert history[0]["active_project"] == result.active_project
        assert history[0]["confidence"] == result.confidence

    async def test_history_empty_db(self, engine):
        conn = await engine.get_conn()

        # Ensure table exists
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS context_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                active_project TEXT,
                confidence TEXT NOT NULL,
                signals_used INTEGER NOT NULL,
                summary TEXT NOT NULL,
                signals_json TEXT,
                projects_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )"""
        )
        await conn.commit()

        inference = ContextInference(conn=conn)
        history = await inference.get_history()
        assert history == []

    async def test_infer_without_persist(self, engine_with_data):
        conn = await engine_with_data.get_conn()
        collector = ContextCollector(
            conn=conn, max_signals=20, git_enabled=False,
            workspace_dir="/nonexistent",
        )
        signals = await collector.collect_all()

        # No conn → no persistence
        inference = ContextInference(conn=None)
        result = inference.infer(signals)
        assert result.active_project is not None


# ─── Full Integration Test ───────────────────────────────────────────


@pytest.mark.asyncio
class TestFullIntegration:
    async def test_end_to_end_context_inference(self, engine_with_data):
        """Full pipeline: collect → infer → verify dominant project."""
        conn = await engine_with_data.get_conn()

        collector = ContextCollector(
            conn=conn, max_signals=30, git_enabled=False,
            workspace_dir="/nonexistent",
        )
        signals = await collector.collect_all()
        assert len(signals) > 0

        inference = ContextInference()
        result = inference.infer(signals)

        # alpha-project has 5 facts, should dominate
        assert result.active_project == "alpha-project"
        assert result.confidence in ("C3", "C4", "C5")
        assert result.signals_used > 0
        assert len(result.projects_ranked) >= 3

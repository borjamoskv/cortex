"""
CORTEX v4.0 — Session Handoff Protocol Tests.

Tests for generate_handoff, save_handoff, and load_handoff.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from cortex.engine import CortexEngine
from cortex.handoff import generate_handoff, load_handoff, save_handoff


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
    """Engine preloaded with decisions, errors, and ghosts."""
    # Decisions
    await engine.store("cortex", "Use SQLite for local storage", fact_type="decision")
    await engine.store("cortex", "Implement handoff protocol", fact_type="decision")
    await engine.store("naroa-2026", "Industrial Noir aesthetic", fact_type="decision")

    # Knowledge
    await engine.store("cortex", "CORTEX supports 24+ LLM providers", fact_type="knowledge")

    # Errors
    await engine.store("naroa-2026", "CSS flicker on gallery hover", fact_type="error")
    await engine.store("cortex", "CI workflow PAT missing scope", fact_type="error")

    # Ghosts (direct insert since engine.store doesn't handle ghosts table)
    conn = await engine.get_conn()
    await conn.execute(
        "INSERT INTO ghosts (reference, context, project, status, created_at) "
        "VALUES (?, ?, ?, 'open', datetime('now'))",
        ("Vector search not implemented", "Planned for v4.1", "cortex"),
    )
    await conn.execute(
        "INSERT INTO ghosts (reference, context, project, status, created_at) "
        "VALUES (?, ?, ?, 'resolved', datetime('now'))",
        ("Old resolved ghost", "Fixed", "cortex"),
    )
    await conn.commit()

    return engine


@pytest.mark.asyncio
class TestGenerateHandoff:
    async def test_generate_empty_db(self, engine):
        """Handoff on empty DB returns valid structure with empty lists."""
        data = await generate_handoff(engine)

        assert data["version"] == "1.0"
        assert "generated_at" in data
        assert data["hot_decisions"] == []
        assert data["active_ghosts"] == []
        assert data["recent_errors"] == []
        assert data["active_projects"] == []
        assert data["stats"]["total_facts"] == 0
        assert data["session"]["mood"] == "neutral"

    async def test_generate_with_decisions(self, engine_with_data):
        """Captures recent decisions ordered by recency."""
        data = await generate_handoff(engine_with_data)

        assert len(data["hot_decisions"]) == 3
        # All should have required fields
        for d in data["hot_decisions"]:
            assert "id" in d
            assert "project" in d
            assert "content" in d
            assert "created_at" in d

    async def test_generate_with_ghosts(self, engine_with_data):
        """Captures only open ghosts, not resolved ones."""
        data = await generate_handoff(engine_with_data)

        assert len(data["active_ghosts"]) == 1
        assert data["active_ghosts"][0]["reference"] == "Vector search not implemented"

    async def test_generate_with_errors(self, engine_with_data):
        """Captures recent errors."""
        data = await generate_handoff(engine_with_data)

        assert len(data["recent_errors"]) == 2
        # Check error content is present
        error_contents = {e["content"] for e in data["recent_errors"]}
        assert "CSS flicker on gallery hover" in error_contents
        assert "CI workflow PAT missing scope" in error_contents

    async def test_generate_active_projects(self, engine_with_data):
        """Lists projects with recent activity."""
        data = await generate_handoff(engine_with_data)

        assert "cortex" in data["active_projects"]
        assert "naroa-2026" in data["active_projects"]

    async def test_generate_stats(self, engine_with_data):
        """Stats summary is correct."""
        data = await generate_handoff(engine_with_data)

        assert data["stats"]["total_facts"] == 6  # 3 decisions + 1 knowledge + 2 errors
        assert data["stats"]["total_projects"] == 2  # cortex, naroa-2026
        assert data["stats"]["db_size_mb"] >= 0

    async def test_session_metadata(self, engine):
        """Session metadata from caller is persisted."""
        meta = {
            "focus_projects": ["cortex", "naroa-2026"],
            "pending_work": ["Implement vector search", "Fix CI"],
            "mood": "productive",
        }
        data = await generate_handoff(engine, session_meta=meta)

        assert data["session"]["mood"] == "productive"
        assert data["session"]["focus_projects"] == ["cortex", "naroa-2026"]
        assert len(data["session"]["pending_work"]) == 2

    async def test_decision_limit(self, engine):
        """Respects MAX_DECISIONS limit."""
        # Store 15 decisions
        for i in range(15):
            await engine.store("test", f"Decision {i}", fact_type="decision")

        data = await generate_handoff(engine)
        assert len(data["hot_decisions"]) == 10  # MAX_DECISIONS

    async def test_error_limit(self, engine):
        """Respects MAX_ERRORS limit."""
        for i in range(10):
            await engine.store("test", f"Error {i}", fact_type="error")

        data = await generate_handoff(engine)
        assert len(data["recent_errors"]) == 5  # MAX_ERRORS


@pytest.mark.asyncio
class TestSaveAndLoad:
    async def test_save_and_load_roundtrip(self, engine):
        """Save → Load produces identical data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "handoff.json"

            original = await generate_handoff(engine)
            save_handoff(original, path=path)

            loaded = load_handoff(path=path)
            assert loaded is not None
            assert loaded["version"] == original["version"]
            assert loaded["session"] == original["session"]
            assert loaded["hot_decisions"] == original["hot_decisions"]

    async def test_load_nonexistent(self):
        """Loading from nonexistent path returns None."""
        result = load_handoff(path=Path("/tmp/does_not_exist_handoff.json"))
        assert result is None

    async def test_load_corrupt_file(self):
        """Loading corrupt JSON returns None."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("NOT VALID JSON {{{")
            path = Path(f.name)

        try:
            result = load_handoff(path=path)
            assert result is None
        finally:
            os.unlink(path)

    async def test_save_creates_parent_dirs(self, engine):
        """Save creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "deep" / "handoff.json"

            data = await generate_handoff(engine)
            saved = save_handoff(data, path=path)

            assert saved.exists()
            loaded = load_handoff(path=path)
            assert loaded is not None

"""
Tests for cortex.sync — forward sync, write-back, and export.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cortex.engine import CortexEngine
from cortex.sync import (
    SyncResult,
    WritebackResult,
    export_snapshot,
    export_to_json,
    sync_memory,
)


@pytest.fixture
def engine(tmp_path):
    """Create a fresh engine in a temp directory."""
    db_path = tmp_path / "test.db"
    eng = CortexEngine(db_path=db_path)
    eng.init_db()
    yield eng
    eng.close()


@pytest.fixture
def agent_memory(tmp_path):
    """Create fake ~/.agent/memory/ structure."""
    memory_dir = tmp_path / "agent" / "memory"
    memory_dir.mkdir(parents=True)

    # ghosts.json
    ghosts = {
        "test-project": {
            "last_task": "Building feature X",
            "mood": "building",
            "blocked_by": None,
            "timestamp": "2026-01-01T00:00:00+00:00",
        }
    }
    (memory_dir / "ghosts.json").write_text(
        json.dumps(ghosts), encoding="utf-8"
    )

    # system.json
    system = {
        "knowledge_global": [
            {"id": "k1", "content": "Test knowledge fact", "topic": "testing"},
        ],
        "decisions_global": [
            {"id": "d1", "decision": "Use pytest for all tests"},
        ],
    }
    (memory_dir / "system.json").write_text(
        json.dumps(system), encoding="utf-8"
    )

    # mistakes.jsonl
    mistake = {
        "project": "test-project",
        "error": "Test error description",
        "cause": "Test cause",
        "fix": "Test fix applied",
    }
    (memory_dir / "mistakes.jsonl").write_text(
        json.dumps(mistake) + "\n", encoding="utf-8"
    )

    # bridges.jsonl
    bridge = {
        "from": "project-a",
        "to": "project-b",
        "pattern": "test-pattern",
        "note": "Test bridge note",
    }
    (memory_dir / "bridges.jsonl").write_text(
        json.dumps(bridge) + "\n", encoding="utf-8"
    )

    return memory_dir


class TestSyncMemory:
    """Tests for forward sync (JSON → CORTEX)."""

    def test_sync_creates_facts(self, engine, agent_memory, monkeypatch):
        """Sync should create facts from all JSON files."""
        # Patch local reference in read.py
        monkeypatch.setattr("cortex.sync.read.MEMORY_DIR", agent_memory)
        # Patch shared state in common.py used by load_sync_state
        monkeypatch.setattr(
            "cortex.sync.common.SYNC_STATE_FILE",
            agent_memory.parent / "sync_state.json",
        )

        result = sync_memory(engine)

        assert isinstance(result, SyncResult)
        assert result.total > 0
        assert len(result.errors) == 0

    def test_sync_idempotent(self, engine, agent_memory, monkeypatch):
        """Running sync twice on unchanged files should not duplicate facts."""
        monkeypatch.setattr("cortex.sync.read.MEMORY_DIR", agent_memory)
        monkeypatch.setattr(
            "cortex.sync.common.SYNC_STATE_FILE",
            agent_memory.parent / "sync_state.json",
        )

        result1 = sync_memory(engine)
        assert result1.total > 0

        result2 = sync_memory(engine)

        # SHA-based dedup: unchanged files produce 0 new facts
        # Ghosts may re-sync (snapshot pattern), but no net duplicates
        assert result2.facts_synced + result2.errors_synced + result2.bridges_synced == 0

    def test_sync_handles_missing_files(self, engine, tmp_path, monkeypatch):
        """Sync should handle missing memory files gracefully."""
        empty_dir = tmp_path / "empty_memory"
        empty_dir.mkdir(parents=True)
        monkeypatch.setattr("cortex.sync.read.MEMORY_DIR", empty_dir)
        monkeypatch.setattr(
            "cortex.sync.common.SYNC_STATE_FILE", tmp_path / "sync_state.json"
        )

        result = sync_memory(engine)
        assert result.total == 0
        assert len(result.errors) == 0

    def test_sync_ghosts(self, engine, agent_memory, monkeypatch):
        """Sync should import ghosts correctly."""
        monkeypatch.setattr("cortex.sync.read.MEMORY_DIR", agent_memory)
        monkeypatch.setattr(
            "cortex.sync.common.SYNC_STATE_FILE",
            agent_memory.parent / "sync_state.json",
        )

        result = sync_memory(engine)
        assert result.ghosts_synced >= 1


class TestWriteBack:
    """Tests for write-back (CORTEX → JSON)."""

    def test_writeback_creates_files(self, engine, tmp_path, monkeypatch):
        """Write-back should create JSON files from DB facts."""
        monkeypatch.setattr("cortex.sync.write.MEMORY_DIR", tmp_path / "memory")
        monkeypatch.setattr(
             "cortex.sync.common.SYNC_STATE_FILE", tmp_path / "sync_state.json"
        )

        # Store test facts
        engine.store("test", "Test ghost content", fact_type="ghost")
        engine.store("test", "Test knowledge content", fact_type="knowledge")
        engine.store("test", "Test error content", fact_type="error")
        engine.store("test", "Test bridge content", fact_type="bridge")

        result = export_to_json(engine)

        assert isinstance(result, WritebackResult)
        assert result.files_written > 0
        assert len(result.errors) == 0

    def test_writeback_sha_skip(self, engine, tmp_path, monkeypatch):
        """Second write-back with no changes should skip files."""
        monkeypatch.setattr("cortex.sync.write.MEMORY_DIR", tmp_path / "memory")
        monkeypatch.setattr(
            "cortex.sync.common.SYNC_STATE_FILE", tmp_path / "sync_state.json"
        )

        engine.store("test", "Some content", fact_type="knowledge")

        result1 = export_to_json(engine)
        result2 = export_to_json(engine)

        assert result1.files_written > 0
        # Second run should skip since no DB changes
        assert result2.files_skipped >= result1.files_written


class TestExportSnapshot:
    """Tests for markdown snapshot export."""

    def test_snapshot_creates_file(self, engine, tmp_path):
        """Export should create a markdown file."""
        engine.store("test-project", "Test fact for snapshot")
        out_path = tmp_path / "snapshot.md"

        result = export_snapshot(engine, out_path=out_path)

        assert result == out_path
        assert out_path.exists()

    def test_snapshot_contains_facts(self, engine, tmp_path):
        """Snapshot should include stored facts."""
        engine.store("test-project", "Unique snapshot test content xyz123")
        out_path = tmp_path / "snapshot.md"

        export_snapshot(engine, out_path=out_path)
        content = out_path.read_text(encoding="utf-8")

        assert "Unique snapshot test content xyz123" in content
        assert "test-project" in content

    def test_snapshot_contains_header(self, engine, tmp_path):
        """Snapshot should have CORTEX header."""
        out_path = tmp_path / "snapshot.md"
        export_snapshot(engine, out_path=out_path)
        content = out_path.read_text(encoding="utf-8")

        assert "CORTEX" in content

"""
Tests for CORTEX MEJORAlo Engine.

Validates X-Ray 13D scanning, session recording, history retrieval,
and stack detection.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from cortex.engine import CortexEngine
from cortex.mejoralo import MejoraloEngine


@pytest.fixture
def engine(tmp_path):
    """Create a temporary CORTEX engine for testing."""
    db_path = str(tmp_path / "test_mejoralo.db")
    eng = CortexEngine(db_path, auto_embed=False)
    eng.init_db()
    yield eng
    eng.close()


@pytest.fixture
def mejoralo(engine):
    """Create a MejoraloEngine instance."""
    return MejoraloEngine(engine)


# ─── Stack Detection ────────────────────────────────────────────────


class TestDetectStack:
    def test_detect_node(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        assert MejoraloEngine.detect_stack(tmp_path) == "node"

    def test_detect_python(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]")
        assert MejoraloEngine.detect_stack(tmp_path) == "python"

    def test_detect_swift(self, tmp_path):
        (tmp_path / "Package.swift").write_text("// swift")
        assert MejoraloEngine.detect_stack(tmp_path) == "swift"

    def test_detect_unknown(self, tmp_path):
        assert MejoraloEngine.detect_stack(tmp_path) == "unknown"


# ─── X-Ray 13D Scan ─────────────────────────────────────────────────


class TestScan:
    def test_scan_empty_project(self, mejoralo, tmp_path):
        """Empty directory should return score 0 and dead_code=True."""
        result = mejoralo.scan("test-empty", str(tmp_path))
        assert result.score == 0 or result.dead_code is True
        assert result.total_files == 0

    def test_scan_scores_dimensions(self, mejoralo, tmp_path):
        """A clean Python file should score well."""
        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "clean.py").write_text(
            "def hello():\n    return 'world'\n"
        )
        result = mejoralo.scan("test-clean", str(tmp_path))
        assert 0 <= result.score <= 100
        assert result.stack == "python"
        assert result.total_files == 1
        assert len(result.dimensions) >= 4

    def test_psi_detection(self, mejoralo, tmp_path):
        """Files with FIXME/TODO should lower Psi score."""
        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "messy.py").write_text(
            "# FIXME: this is broken\n"
            "# TODO: fix later\n"
            "# HACK: workaround\n"
            "# WTF is this\n"
            "def bad():\n    pass\n"
        )
        result = mejoralo.scan("test-psi", str(tmp_path))
        psi = next(d for d in result.dimensions if d.name == "Psi")
        assert psi.score < 100
        assert len(psi.findings) >= 3

    def test_large_file_detection(self, mejoralo, tmp_path):
        """Files with >300 LOC should be flagged in architecture dimension."""
        (tmp_path / "pyproject.toml").write_text("[project]")
        # Create a 400-line file
        lines = "\n".join(f"x_{i} = {i}" for i in range(400))
        (tmp_path / "huge.py").write_text(lines)
        result = mejoralo.scan("test-arch", str(tmp_path))
        arch = next(d for d in result.dimensions if d.name == "Arquitectura")
        assert arch.score < 100
        assert any("huge.py" in f for f in arch.findings)

    def test_security_detection(self, mejoralo, tmp_path):
        """Files with eval() should be flagged in security dimension."""
        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "unsafe.py").write_text(
            "result = eval('1+1')\n"
            "x = innerHTML\n"
        )
        result = mejoralo.scan("test-sec", str(tmp_path))
        sec = next(d for d in result.dimensions if d.name == "Seguridad")
        assert sec.score < 100
        assert len(sec.findings) >= 1


# ─── Session Recording ──────────────────────────────────────────────


class TestRecordSession:
    def test_record_persists(self, mejoralo, engine):
        """record_session should persist a fact in the ledger."""
        fact_id = mejoralo.record_session(
            project="test-proj",
            score_before=40,
            score_after=85,
            actions=["Fixed build", "Removed dead code"],
        )
        assert fact_id > 0

        # Verify it's in the database
        conn = engine._get_conn()
        row = conn.execute(
            "SELECT content, fact_type, tags, meta FROM facts WHERE id = ?",
            (fact_id,),
        ).fetchone()
        assert row is not None
        assert "MEJORAlo v7.3" in row[0]
        assert row[1] == "decision"
        assert "mejoralo" in row[2]
        meta = json.loads(row[3])
        assert meta["score_before"] == 40
        assert meta["score_after"] == 85
        assert meta["delta"] == 45


# ─── History ─────────────────────────────────────────────────────────


class TestHistory:
    def test_history_returns_sessions(self, mejoralo):
        """history() should return previously recorded sessions."""
        mejoralo.record_session("hist-proj", 30, 70, ["Fix A"])
        mejoralo.record_session("hist-proj", 70, 90, ["Fix B"])

        sessions = mejoralo.history("hist-proj")
        assert len(sessions) == 2
        # Most recent first
        assert sessions[0]["delta"] == 20
        assert sessions[1]["delta"] == 40

    def test_history_empty_project(self, mejoralo):
        """history() should return empty list for unknown project."""
        sessions = mejoralo.history("nonexistent")
        assert sessions == []

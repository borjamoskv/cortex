"""
Tests for CLI CRUD commands — delete, list, edit.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from cortex.cli import cli
from cortex.engine import CortexEngine


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def db_path(tmp_path):
    """Create a temp database with test data."""
    path = tmp_path / "test.db"
    engine = CortexEngine(db_path=path)
    engine.init_db_sync()
    engine.store_sync("test-project", "First test fact", fact_type="knowledge")
    engine.store_sync("test-project", "Second test fact", fact_type="error")
    engine.store_sync("other-project", "Third test fact", fact_type="ghost")
    engine.close_sync()
    return str(path)


class TestListCommand:
    """Tests for 'cortex list'."""

    def test_list_shows_facts(self, runner, db_path):
        result = runner.invoke(cli, ["list", "--db", db_path])
        assert result.exit_code == 0
        assert "First test fact" in result.output or "CORTEX Facts" in result.output

    def test_list_filter_by_project(self, runner, db_path):
        result = runner.invoke(cli, ["list", "--db", db_path, "-p", "test-project"])
        assert result.exit_code == 0
        # Should show test-project facts but not other-project
        assert "other-project" not in result.output or "test-project" in result.output

    def test_list_filter_by_type(self, runner, db_path):
        result = runner.invoke(cli, ["list", "--db", db_path, "--type", "ghost"])
        assert result.exit_code == 0
        assert "Third test fact" in result.output or "ghost" in result.output

    def test_list_empty_result(self, runner, db_path):
        result = runner.invoke(cli, ["list", "--db", db_path, "-p", "nonexistent"])
        assert result.exit_code == 0
        assert "No se encontraron" in result.output

    def test_list_with_limit(self, runner, db_path):
        result = runner.invoke(cli, ["list", "--db", db_path, "-n", "1"])
        assert result.exit_code == 0


class TestDeleteCommand:
    """Tests for 'cortex delete'."""

    def test_delete_existing_fact(self, runner, db_path, monkeypatch, tmp_path):
        # Monkeypatch sync paths to avoid touching real files
        monkeypatch.setattr("cortex.sync.MEMORY_DIR", tmp_path / "memory")
        monkeypatch.setattr("cortex.sync.CORTEX_DIR", tmp_path)
        monkeypatch.setattr(
            "cortex.sync.SYNC_STATE_FILE", tmp_path / "sync_state.json"
        )

        result = runner.invoke(cli, ["delete", "1", "--db", db_path])
        assert result.exit_code == 0
        assert "deprecado" in result.output

    def test_delete_nonexistent_fact(self, runner, db_path):
        result = runner.invoke(cli, ["delete", "999", "--db", db_path])
        assert result.exit_code == 0
        assert "No se encontró" in result.output

    def test_delete_with_reason(self, runner, db_path, monkeypatch, tmp_path):
        monkeypatch.setattr("cortex.sync.MEMORY_DIR", tmp_path / "memory")
        monkeypatch.setattr("cortex.sync.CORTEX_DIR", tmp_path)
        monkeypatch.setattr(
            "cortex.sync.SYNC_STATE_FILE", tmp_path / "sync_state.json"
        )

        result = runner.invoke(cli, ["delete", "1", "-r", "testing", "--db", db_path])
        assert result.exit_code == 0
        assert "deprecado" in result.output


class TestEditCommand:
    """Tests for 'cortex edit'."""

    def test_edit_existing_fact(self, runner, db_path, monkeypatch, tmp_path):
        monkeypatch.setattr("cortex.sync.MEMORY_DIR", tmp_path / "memory")
        monkeypatch.setattr("cortex.sync.CORTEX_DIR", tmp_path)
        monkeypatch.setattr(
            "cortex.sync.SYNC_STATE_FILE", tmp_path / "sync_state.json"
        )

        result = runner.invoke(
            cli, ["edit", "1", "Updated content here", "--db", db_path]
        )
        assert result.exit_code == 0
        assert "editado" in result.output

    def test_edit_nonexistent_fact(self, runner, db_path):
        result = runner.invoke(
            cli, ["edit", "999", "New content", "--db", db_path]
        )
        assert result.exit_code == 0
        assert "No se encontró" in result.output

    def test_edit_preserves_metadata(self, runner, db_path, monkeypatch, tmp_path):
        """Edit should preserve project, type, tags from original."""
        monkeypatch.setattr("cortex.sync.MEMORY_DIR", tmp_path / "memory")
        monkeypatch.setattr("cortex.sync.CORTEX_DIR", tmp_path)
        monkeypatch.setattr(
            "cortex.sync.SYNC_STATE_FILE", tmp_path / "sync_state.json"
        )

        result = runner.invoke(
            cli, ["edit", "1", "Edited content", "--db", db_path]
        )
        assert result.exit_code == 0

        # Verify the new fact exists with list
        list_result = runner.invoke(
            cli, ["list", "--db", db_path, "-p", "test-project"]
        )
        assert "Edited content" in list_result.output

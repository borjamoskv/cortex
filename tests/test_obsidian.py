"""Tests for cortex.sync.obsidian — Obsidian vault export."""

from __future__ import annotations

import pytest

from cortex.engine import CortexEngine
from cortex.sync.obsidian import (
    _render_fact_note,
    _render_frontmatter,
    _render_project_moc,
    _render_tag_note,
    _slugify,
    export_obsidian,
)


@pytest.fixture
def engine(tmp_path):
    """Create a fresh engine in a temp directory."""
    db_path = tmp_path / "test.db"
    eng = CortexEngine(db_path=db_path)
    eng.init_db_sync()
    yield eng
    eng.close_sync()


# ─── Unit tests for helpers ──────────────────────────────────────────


class TestSlugify:
    def test_basic(self):
        assert _slugify("hello world") == "hello-world"

    def test_special_chars(self):
        assert _slugify("auth/login (v2)") == "authlogin-v2"

    def test_truncation(self):
        long = "a" * 200
        assert len(_slugify(long)) <= 80


class TestRenderFrontmatter:
    def test_string_values(self):
        result = _render_frontmatter({"key": "value"})
        assert '---' in result
        assert 'key: "value"' in result

    def test_number_values(self):
        result = _render_frontmatter({"score": 0.95})
        assert "score: 0.95" in result

    def test_list_values(self):
        result = _render_frontmatter({"tags": ["a", "b"]})
        assert "tags: [a, b]" in result

    def test_empty_list(self):
        result = _render_frontmatter({"tags": []})
        assert "tags: []" in result

    def test_null_value(self):
        result = _render_frontmatter({"x": None})
        assert "x: null" in result


class TestRenderFactNote:
    def test_contains_frontmatter(self):
        fact = {
            "id": 42,
            "type": "decision",
            "project": "cortex",
            "content": "Use SQLite for storage",
            "confidence": "confirmed",
            "tags": ["architecture", "storage"],
            "consensus_score": 1.0,
            "created_at": "2026-01-15T10:00:00",
            "updated_at": "2026-01-15T10:00:00",
            "active": True,
        }
        result = _render_fact_note(fact)

        assert result.startswith("---")
        assert "id: 42" in result
        assert 'type: "decision"' in result

    def test_contains_wikilinks(self):
        fact = {
            "id": 1,
            "type": "knowledge",
            "project": "naroa-2026",
            "content": "Test content",
            "confidence": "stated",
            "tags": ["css", "animation"],
            "consensus_score": 1.0,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": None,
            "active": True,
        }
        result = _render_fact_note(fact)

        assert "[[naroa-2026]]" in result
        assert "[[css]]" in result
        assert "[[animation]]" in result

    def test_no_tags(self):
        fact = {
            "id": 1,
            "type": "error",
            "project": "test",
            "content": "Error occurred",
            "confidence": "confirmed",
            "tags": [],
            "consensus_score": 1.0,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": None,
            "active": True,
        }
        result = _render_fact_note(fact)

        assert "**Tags:**" not in result


class TestRenderProjectMOC:
    def test_contains_project_name(self):
        facts = [
            {"id": 1, "type": "decision", "content": "Do X", "project": "cortex"},
            {"id": 2, "type": "knowledge", "content": "Y works", "project": "cortex"},
        ]
        result = _render_project_moc("cortex", facts)

        assert "cortex" in result
        assert "2 active facts" in result

    def test_groups_by_type(self):
        facts = [
            {"id": 1, "type": "decision", "content": "Do X", "project": "test"},
            {"id": 2, "type": "error", "content": "Bug Y", "project": "test"},
        ]
        result = _render_project_moc("test", facts)

        assert "Decision" in result
        assert "Error" in result


class TestRenderTagNote:
    def test_basic(self):
        facts = [
            {"id": 1, "type": "decision", "content": "Test content", "project": "p1"},
        ]
        result = _render_tag_note("auth", facts)

        assert "auth" in result
        assert "1 facts tagged" in result


# ─── Integration tests ───────────────────────────────────────────────


class TestExportObsidian:
    @pytest.mark.asyncio
    async def test_empty_vault(self, engine, tmp_path):
        """Export with no facts should create dashboard and folder structure."""
        vault = tmp_path / "vault"
        stats = await export_obsidian(engine, vault)

        assert stats["total_facts"] == 0
        assert stats["notes_created"] == 1  # Dashboard only
        assert (vault / "🧠 CORTEX Dashboard.md").exists()
        assert (vault / "projects").is_dir()
        assert (vault / "tags").is_dir()
        assert (vault / "decisions").is_dir()

    @pytest.mark.asyncio
    async def test_vault_with_facts(self, engine, tmp_path):
        """Export should create individual notes for each fact."""
        engine.store_sync("cortex", "Use SQLite", fact_type="decision", tags=["arch"])
        engine.store_sync("cortex", "Import failed", fact_type="error")
        engine.store_sync("naroa-2026", "Gallery redesign", fact_type="ghost")

        vault = tmp_path / "vault"
        stats = await export_obsidian(engine, vault)

        # 3 facts + 2 project MOCs + 1 tag + 1 dashboard = 7
        assert stats["total_facts"] == 3
        assert stats["notes_created"] == 7
        assert len(stats["projects"]) == 2
        assert "cortex" in stats["projects"]
        assert "naroa-2026" in stats["projects"]

    @pytest.mark.asyncio
    async def test_fact_note_files(self, engine, tmp_path):
        """Exported fact notes should exist with correct content."""
        fact_id = engine.store_sync(
            "cortex", "Obsidian integration complete", fact_type="decision"
        )

        vault = tmp_path / "vault"
        await export_obsidian(engine, vault)

        note_path = vault / "decisions" / f"decision-{fact_id}.md"
        assert note_path.exists()

        content = note_path.read_text(encoding="utf-8")
        assert "---" in content
        assert "Obsidian integration complete" in content
        assert "[[cortex]]" in content

    @pytest.mark.asyncio
    async def test_project_moc(self, engine, tmp_path):
        """Project MOC should link to its facts."""
        engine.store_sync("cortex", "Fact A", fact_type="decision")
        engine.store_sync("cortex", "Fact B", fact_type="knowledge")

        vault = tmp_path / "vault"
        await export_obsidian(engine, vault)

        moc_path = vault / "projects" / "cortex.md"
        assert moc_path.exists()

        content = moc_path.read_text(encoding="utf-8")
        assert "cortex" in content
        assert "Decision" in content
        assert "Knowledge" in content

    @pytest.mark.asyncio
    async def test_tag_index(self, engine, tmp_path):
        """Tag index notes should exist and link back."""
        engine.store_sync("test", "Tagged fact", fact_type="knowledge", tags=["auth"])

        vault = tmp_path / "vault"
        await export_obsidian(engine, vault)

        tag_path = vault / "tags" / "auth.md"
        assert tag_path.exists()

        content = tag_path.read_text(encoding="utf-8")
        assert "auth" in content
        assert "Tagged fact" in content

    @pytest.mark.asyncio
    async def test_dashboard_overview(self, engine, tmp_path):
        """Dashboard should show project and type overview."""
        engine.store_sync("p1", "Decision 1", fact_type="decision")
        engine.store_sync("p2", "Error 1", fact_type="error")

        vault = tmp_path / "vault"
        await export_obsidian(engine, vault)

        dashboard = (vault / "🧠 CORTEX Dashboard.md").read_text(encoding="utf-8")
        assert "CORTEX Dashboard" in dashboard
        assert "p1" in dashboard
        assert "p2" in dashboard
        assert "decision" in dashboard
        assert "error" in dashboard

    @pytest.mark.asyncio
    async def test_idempotent_export(self, engine, tmp_path):
        """Running export twice should produce same vault without errors."""
        engine.store_sync("test", "Some fact", fact_type="knowledge")

        vault = tmp_path / "vault"
        stats1 = await export_obsidian(engine, vault)
        stats2 = await export_obsidian(engine, vault)

        assert stats1["notes_created"] == stats2["notes_created"]
        assert stats1["total_facts"] == stats2["total_facts"]

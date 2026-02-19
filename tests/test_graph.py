"""Tests for CORTEX Graph Memory."""

import pytest

import os
os.environ["CORTEX_GRAPH_BACKEND"] = "sqlite"

from cortex.engine import CortexEngine

from cortex.graph import (
    SQLiteBackend,
    detect_relationships,
    extract_entities,
)


@pytest.fixture
def engine(tmp_path):
    """Create a test engine with graph tables."""
    db_path = tmp_path / "test_graph.db"
    # Use sync initialization
    eng = CortexEngine(db_path=str(db_path), auto_embed=False)
    eng.init_db_sync()
    return eng


class TestEntityExtraction:
    """Tests for extract_entities()."""

    def test_extract_file_entities(self):
        entities = extract_entities("Modified engine.py and search.py for hybrid search")
        names = [e["name"] for e in entities]
        assert "engine.py" in names
        assert "search.py" in names

    def test_extract_tool_entities(self):
        entities = extract_entities("We use SQLite and FastAPI for the backend")
        names = [e["name"].lower() for e in entities]
        assert "sqlite" in names
        assert "fastapi" in names

    def test_extract_class_entities(self):
        entities = extract_entities("The CortexEngine class handles all storage")
        names = [e["name"] for e in entities]
        assert "CortexEngine" in names

    def test_extract_project_pattern(self):
        entities = extract_entities("Working on cortex-memory and naroa-2026 projects")
        names = [e["name"] for e in entities]
        assert "cortex-memory" in names
        assert "naroa-2026" in names

    def test_no_duplicates(self):
        entities = extract_entities("SQLite is great. SQLite is fast.")
        sqlite_ents = [e for e in entities if e["name"].lower() == "sqlite"]
        assert len(sqlite_ents) == 1

    def test_empty_input(self):
        assert extract_entities("") == []
        assert extract_entities("hello world") == []


class TestRelationshipDetection:
    """Tests for detect_relationships()."""

    def test_detect_relationships_cooccurrence(self):
        entities = [
            {"name": "SQLite", "entity_type": "tool"},
            {"name": "FastAPI", "entity_type": "tool"},
        ]
        rels = detect_relationships("uses SQLite with FastAPI", entities)
        assert len(rels) >= 1
        assert rels[0]["relation_type"] == "uses"

    def test_detect_depends_on(self):
        entities = [
            {"name": "engine.py", "entity_type": "file"},
            {"name": "SQLite", "entity_type": "tool"},
        ]
        rels = detect_relationships("engine.py depends on SQLite", entities)
        assert rels[0]["relation_type"] == "depends_on"

    def test_no_relationships_single_entity(self):
        entities = [{"name": "SQLite", "entity_type": "tool"}]
        rels = detect_relationships("Uses SQLite", entities)
        assert len(rels) == 0

    def test_no_relationships_empty(self):
        assert detect_relationships("hello", []) == []


class TestGraphDBOperations:
    """Tests for database-backed graph operations."""

    def test_upsert_entity_new(self, engine):
        conn = engine._get_sync_conn()
        eid = SQLiteBackend(conn).upsert_entity_sync(
            "SQLite", "tool", "cortex", "2025-01-01T00:00:00"
        )
        assert eid > 0
        conn.commit()

    def test_upsert_entity_existing(self, engine):
        conn = engine._get_sync_conn()
        backend = SQLiteBackend(conn)
        eid1 = backend.upsert_entity_sync("SQLite", "tool", "cortex", "2025-01-01T00:00:00")
        conn.commit()
        eid2 = backend.upsert_entity_sync("SQLite", "tool", "cortex", "2025-01-02T00:00:00")
        conn.commit()
        assert eid1 == eid2
        # Check mention count incremented
        row = conn.execute("SELECT mention_count FROM entities WHERE id = ?", (eid1,)).fetchone()
        assert row[0] == 2

    def test_process_fact_graph(self, engine):
        from cortex.graph import process_fact_graph_sync

        conn = engine._get_sync_conn()
        # Insert a fact row so FK constraint is satisfied
        fact_id = engine.store_sync("cortex", "CORTEX uses SQLite and FastAPI for storage")
        ent_count, rel_count = process_fact_graph_sync(
            conn,
            fact_id,
            "CORTEX uses SQLite and FastAPI for storage",
            "cortex",
            "2025-01-01T00:00:00",
        )
        conn.commit()
        assert ent_count >= 2
        assert rel_count >= 1


class TestGraphQueries:
    """Tests for graph query operations."""

    def test_get_graph_empty(self, engine):
        data = engine.graph_sync(project="empty_project")
        assert data["entities"] == []
        assert data["relationships"] == []

    def test_get_graph_with_data(self, engine):
        # Store some facts to build graph
        engine.store_sync("test", "The CortexEngine class uses SQLite for storage")
        engine.store_sync("test", "FastAPI serves the API endpoints using Python")
        data = engine.graph_sync(project="test")
        assert len(data["entities"]) > 0
        assert data["stats"]["total_entities"] > 0

    def test_query_entity_found(self, engine):
        engine.store_sync("test", "SQLite is the database engine used by CORTEX")
        result = engine.query_entity_sync("SQLite", project="test")
        assert result is not None
        assert result["name"] == "SQLite"
        assert result["mentions"] >= 1

    def test_query_entity_not_found(self, engine):
        result = engine.query_entity_sync("NonexistentEntity")
        assert result is None


class TestEngineGraphIntegration:
    """Test that store() auto-extracts entities."""

    def test_store_auto_extracts(self, engine):
        engine.store_sync("myproject", "Implemented search.py using SQLite and FastAPI")
        data = engine.graph_sync(project="myproject")
        names = [e["name"] for e in data["entities"]]
        assert any("search.py" in n for n in names)

    def test_store_builds_relationships(self, engine):
        engine.store_sync("test", "engine.py depends on SQLite for data storage")
        data = engine.graph_sync(project="test")
        assert len(data["relationships"]) >= 1

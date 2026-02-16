"""Tests for Ghost Resolution."""
import pytest
from cortex.engine import CortexEngine

@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "test_ghosts.db"
    eng = CortexEngine(db_path=str(db_path), auto_embed=False)
    eng.init_db_sync()
    yield eng
    eng.close_sync()

def test_register_ghost(engine):
    gid = engine.register_ghost_sync("UnknownRef", "Context: ...", "test-project")
    assert gid > 0
    
    # Verify it exists in DB
    conn = engine._get_sync_conn()
    row = conn.execute("SELECT reference, status FROM ghosts WHERE id = ?", (gid,)).fetchone()
    assert row[0] == "UnknownRef"
    assert row[1] == "open"

def test_resolve_ghost(engine):
    gid = engine.register_ghost_sync("GhostRef", "Context...", "test-project")
    
    # Create target entity to link to
    conn = engine._get_sync_conn()
    cursor = conn.execute(
        "INSERT INTO entities (name, entity_type, project, first_seen, last_seen, mention_count) "
        "VALUES ('RealEntity', 'test', 'test-project', '2025-01-01', '2025-01-01', 1)"
    )
    target_id = cursor.lastrowid
    conn.commit()
    
    resolved = engine.resolve_ghost_sync(gid, target_id, confidence=0.95)
    assert resolved is True
    
    # Verify status
    row = conn.execute("SELECT status, target_id, confidence FROM ghosts WHERE id = ?", (gid,)).fetchone()
    assert row[0] == "resolved"
    assert row[1] == target_id
    assert row[2] == 0.95

def test_idempotent_register(engine):
    gid1 = engine.register_ghost_sync("Ref1", "C1", "p1")
    gid2 = engine.register_ghost_sync("Ref1", "C2", "p1")
    assert gid1 == gid2

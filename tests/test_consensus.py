import pytest
import os
import unittest.mock as mock

# Integration test for the Consensus System

@pytest.fixture(scope="function")
def client(monkeypatch):
    test_db = "test_consensus_final.db"
    # Clean up any leftover db files
    for suffix in ("", "-wal", "-shm"):
        path = test_db + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    # Patch environment
    monkeypatch.setenv("CORTEX_DB", test_db)
    
    import cortex.config
    monkeypatch.setattr(cortex.config, "DB_PATH", test_db)

    # Now import app and state
    from cortex.api import app
    from cortex import api_state
    import cortex.auth
    from fastapi.testclient import TestClient

    # Set up some test state
    monkeypatch.setattr(cortex.api, "DB_PATH", test_db)
    monkeypatch.setattr(cortex.auth, "_auth_manager", None)

    with TestClient(app) as c:
        raw_key, _ = api_state.auth_manager.create_key(
            "test_agent",
            tenant_id="test_proj",
            permissions=["read", "write", "admin"],
        )
        c.headers = {"Authorization": f"Bearer {raw_key}"}
        yield c


def test_consensus_flow(client):
    """Test standard consensus flow (upvote/downvote)."""
    # 1. Register agent
    resp = client.post("/v1/agents", json={"name": "test-agent", "agent_type": "ai"})
    assert resp.status_code == 200
    agent_id = resp.json()["agent_id"]

    # 2. Store fact
    resp = client.post("/v1/facts", json={"project": "test_proj", "content": "The Earth is round"})
    assert resp.status_code == 200
    fact_id = resp.json()["fact_id"]

    # 3. Upvote
    resp = client.post(f"/v1/facts/{fact_id}/vote", json={"agent_id": agent_id, "vote": 1})
    assert resp.status_code == 200
    assert resp.json()["new_score"] > 1.0

    # 4. Downvote from same agent (updates existing vote)
    resp = client.post(f"/v1/facts/{fact_id}/vote", json={"agent_id": agent_id, "vote": -1})
    assert resp.status_code == 200
    assert resp.json()["new_score"] < 1.0


def test_recall_ordering(client):
    """Test standard recall ordering (score + recency)."""
    from cortex import api_state
    engine = api_state.engine

    # 1. Store 3 facts
    engine.store_sync("test_proj", "Fact A")
    engine.store_sync("test_proj", "Fact B")
    fid_c = engine.store_sync("test_proj", "Fact C")

    # 2. Add some votes to Fact C (Upvote)
    resp = client.post("/v1/agents", json={"name": "vote-agent", "agent_type": "ai"})
    agent_id = resp.json()["agent_id"]

    client.post(f"/v1/facts/{fid_c}/vote", json={"agent_id": agent_id, "vote": 1})

    # 3. Recall and check order (Fact C should be first)
    resp = client.get("/v1/recall?project=test_proj")
    facts = resp.json()
    assert facts[0]["content"] == "Fact C"


def test_rwc_flow(client):
    """Test Reputation-Weighted Consensus flow."""
    from cortex import api_state
    engine = api_state.engine

    # 1. Register 2 agents
    resp1 = client.post("/v1/agents", json={"name": "whale", "agent_type": "ai"})
    agent_whale = resp1.json()["agent_id"]

    resp2 = client.post("/v1/agents", json={"name": "shrimp", "agent_type": "ai"})
    agent_shrimp = resp2.json()["agent_id"]

    # 2. Boost reputation in DB
    conn = engine._get_sync_conn()
    conn.execute("UPDATE agents SET reputation_score = 10.0 WHERE id = ?", (agent_whale,))
    conn.execute("UPDATE agents SET reputation_score = 1.0 WHERE id = ?", (agent_shrimp,))
    conn.commit()

    # 3. Store a fact
    fid = engine.store_sync("test_proj", "Reputation Test Fact")

    # 4. Shrimp downvotes (-1), Whale upvotes (+1)
    client.post(f"/v1/facts/{fid}/vote", json={"agent_id": agent_shrimp, "vote": -1})
    client.post(f"/v1/facts/{fid}/vote", json={"agent_id": agent_whale, "vote": 1})

    # 5. Check score (should be > 1.0 because whale has more weight)
    resp_recall = client.get("/v1/recall?project=test_proj")
    fact = next(f for f in resp_recall.json() if f["fact_id"] == fid)
    
    assert fact["consensus_score"] > 1.0
    assert fact["confidence"] == "verified"

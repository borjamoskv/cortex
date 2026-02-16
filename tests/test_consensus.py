
import pytest
import os
import sqlite3
from fastapi.testclient import TestClient
from cortex.api import app
from cortex import api_state
import cortex.auth
import cortex.config
from cortex.engine import CortexEngine
from cortex.auth import AuthManager
from cortex.timing import TimingTracker

# Integration test for the Consensus System

@pytest.fixture(scope="function")
def client(monkeypatch):
    test_db = "test_consensus_final.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Patch DB_PATH in modules before TestClient starts lifespan
    monkeypatch.setenv("CORTEX_DB", test_db)
    monkeypatch.setattr(cortex.config, "DB_PATH", test_db)
    monkeypatch.setattr(cortex.api, "DB_PATH", test_db)
    monkeypatch.setattr(cortex.auth, "DB_PATH", test_db)
    
    # Clear the AuthManager singleton to force restart with new DB
    monkeypatch.setattr(cortex.auth, "_auth_manager", None)
    
    with TestClient(app) as c:
        # After lifespan start, api_state should be initialized with test_db
        # We need an admin key to proceed
        raw_key, api_key = api_state.auth_manager.create_key(
            "test_agent", 
            tenant_id="test_proj",
            permissions=["read", "write", "admin"]
        )
        c.headers = {"Authorization": f"Bearer {raw_key}"}
        yield c
    
    if getattr(api_state, "engine", None):
        api_state.engine.close()
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except OSError:
            pass

def test_consensus_flow(client):
    # 1. Store a fact
    resp = client.post("/v1/facts", json={
        "project": "test_proj",
        "content": "Consensus test fact",
        "fact_type": "knowledge"
    })
    assert resp.status_code == 200, resp.json()
    fact_id = resp.json()["fact_id"]
    
    # 2. Check initial state
    resp = client.get(f"/v1/projects/test_proj/facts")
    assert resp.status_code == 200
    fact = next(f for f in resp.json() if f["id"] == fact_id)
    assert fact["consensus_score"] == 1.0
    assert fact["confidence"] == "stated"
    
    # 3. Vote UP
    resp = client.post(f"/v1/facts/{fact_id}/vote", json={"value": 1})
    assert resp.status_code == 200, resp.json()
    assert resp.json()["new_consensus_score"] == 1.1
    assert resp.json()["agent"] == "test_agent"
    
    # Engine direct votes to reach threshold (+5 net votes needed for 'verified' at 1.5)
    for i in range(4):
        api_state.engine.vote(fact_id, f"agent_{i}", 1)
        
    # 4. Verify shifted confidence
    resp = client.get(f"/v1/projects/test_proj/facts")
    fact = next(f for f in resp.json() if f["id"] == fact_id)
    assert fact["consensus_score"] == 1.5
    assert fact["confidence"] == "verified"

def test_recall_ordering(client):
    proj = "test_proj_ordering"
    
    # Let's just create a new key for this proj
    raw_key, api_key = api_state.auth_manager.create_key("voter_agent", tenant_id=proj)
    client.headers = {"Authorization": f"Bearer {raw_key}"}

    # Store old fact with high consensus
    resp = client.post("/v1/facts", json={"project": proj, "content": "Verified Old"})
    assert resp.status_code == 200
    fid_old = resp.json()["fact_id"]
    for i in range(10): 
        api_state.engine.vote(fid_old, f"voter_{i}", 1) # Score = 2.0
        
    # Store new fact (Score = 1.0)
    resp = client.post("/v1/facts", json={"project": proj, "content": "Stated New"})
    fid_new = resp.json()["fact_id"]
    
    # Store disputed fact
    resp = client.post("/v1/facts", json={"project": proj, "content": "Disputed"})
    fid_bad = resp.json()["fact_id"]
    for i in range(6): 
        api_state.engine.vote(fid_bad, f"hater_{i}", -1) # Score = 0.4
    
    # Recall and check order
    resp = client.get(f"/v1/projects/{proj}/facts")
    facts = resp.json()
    
    ids = [f["id"] for f in facts]
    # Ordering: (Score * 0.8 + Recency * 0.2)
    assert ids[0] == fid_old
    assert ids[1] == fid_new
    assert ids[2] == fid_bad


def test_rwc_flow(client):
    """Test the Reputation-Weighted Consensus (v2)."""
    # 1. Register agents
    resp = client.post("/v1/agents", json={"name": "Agent_Alpha", "agent_type": "ai"})
    assert resp.status_code == 200
    alpha_id = resp.json()["agent_id"]
    
    resp = client.post("/v1/agents", json={"name": "Agent_Beta", "agent_type": "ai"})
    assert resp.status_code == 200
    beta_id = resp.json()["agent_id"]

    # 2. Store fact
    resp = client.post("/v1/facts", json={
        "project": "test_proj",
        "content": "RWC test fact"
    })
    fact_id = resp.json()["fact_id"]

    # 3. Vote with Alpha (Rep 0.5)
    resp = client.post(f"/v1/facts/{fact_id}/vote-v2", json={
        "agent_id": alpha_id,
        "vote": 1,
        "reason": "Verified by Alpha"
    })
    assert resp.status_code == 200
    # Score should be 2.0 because it's the only vote
    assert resp.json()["new_consensus_score"] == 2.0
    
    # 4. Vote AGAINST with Beta (Rep 0.5) -> Should cancel out to 1.0
    resp = client.post(f"/v1/facts/{fact_id}/vote-v2", json={
        "agent_id": beta_id,
        "vote": -1,
        "reason": "Disputed by Beta"
    })
    assert resp.status_code == 200
    assert resp.json()["new_consensus_score"] == 1.0

    # 5. Manually boost Alpha's reputation and vote again
    with api_state.engine._get_conn() as conn:
        conn.execute("UPDATE agents SET reputation_score = 0.9 WHERE id = ?", (alpha_id,))
        conn.commit()

    # Alpha votes again (updates existing vote)
    resp = client.post(f"/v1/facts/{fact_id}/vote-v2", json={
        "agent_id": alpha_id,
        "vote": 1
    })
    score = resp.json()["new_consensus_score"]
    assert 1.28 < score < 1.29

import pytest
import os
from fastapi.testclient import TestClient
from cortex.api import app
from cortex.auth import AuthManager
from cortex.engine import CortexEngine
from cortex import api_state


@pytest.fixture
def client():
    # Setup test DB
    test_db = "test_consensus_security.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize engine and auth with test DB
    import cortex.auth

    # Create the test engine and auth manager
    test_engine = CortexEngine(test_db)
    test_engine.init_db()
    test_auth_manager = AuthManager(test_db)

    # Save old globals
    old_engine = api_state.engine
    old_auth = api_state.auth_manager
    old_cortex_auth = cortex.auth._auth_manager

    with TestClient(app) as c:
        # Re-patch after lifespan runs
        api_state.engine = test_engine
        api_state.auth_manager = test_auth_manager
        import cortex.auth

        cortex.auth._auth_manager = test_auth_manager
        yield c

    # Cleanup
    test_engine.close()
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except OSError:
            pass

    # Restore Globals
    api_state.engine = old_engine
    api_state.auth_manager = old_auth
    cortex.auth._auth_manager = old_cortex_auth


def test_consensus_tenant_isolation(client):
    # 1. Create two tenants using AuthManager directly
    am = api_state.auth_manager
    raw_key1, _ = am.create_key("T1", "tenant1", ["read", "write"])
    raw_key2, _ = am.create_key("T2", "tenant2", ["read", "write"])

    # 2. Tenant 1 stores a fact
    resp = client.post(
        "/v1/facts",
        json={"project": "tenant1", "content": "Fact from T1"},
        headers={"Authorization": f"Bearer {raw_key1}"},
    )
    assert resp.status_code == 200, f"Setup failed: {resp.text}"
    fact_id = resp.json()["fact_id"]

    # 3. Tenant 2 tries to vote on Tenant 1's fact (Should fail 403)
    resp = client.post(
        f"/v1/facts/{fact_id}/vote",
        json={"value": 1},
        headers={"Authorization": f"Bearer {raw_key2}"},
    )
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"]

    # 4. Tenant 2 tries to read votes for Tenant 1's fact (Should fail 403)
    resp = client.get(f"/v1/facts/{fact_id}/votes", headers={"Authorization": f"Bearer {raw_key2}"})
    assert resp.status_code == 403

    # 5. Tenant 1 votes on their own fact (Should succeed)
    resp = client.post(
        f"/v1/facts/{fact_id}/vote",
        json={"value": 1},
        headers={"Authorization": f"Bearer {raw_key1}"},
    )
    assert resp.status_code == 200
    assert resp.json()["new_consensus_score"] > 1.0


def test_vote_validation(client):
    am = api_state.auth_manager
    raw_key1, _ = am.create_key("T1", "tenant1", ["read", "write"])

    resp = client.post(
        "/v1/facts",
        json={"project": "tenant1", "content": "Fact from T1"},
        headers={"Authorization": f"Bearer {raw_key1}"},
    )
    assert resp.status_code == 200
    fact_id = resp.json()["fact_id"]

    # Test invalid vote value
    resp = client.post(
        f"/v1/facts/{fact_id}/vote",
        json={"agent": "tester", "vote": 5},
        headers={"Authorization": f"Bearer {raw_key1}"},
    )
    assert resp.status_code == 422  # Pydantic validation error

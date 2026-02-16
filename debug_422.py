import os
import tempfile
import json
from fastapi.testclient import TestClient

# Setup test environment
_test_db = tempfile.mktemp(suffix=".db")
os.environ["CORTEX_DB"] = _test_db

from cortex.api import app

with TestClient(app) as client:
    # Bootstrap API key
    resp = client.post("/v1/admin/keys?name=test-key&tenant_id=test")
    api_key = resp.json()["key"]
    auth_headers = {"Authorization": f"Bearer {api_key}"}

    # Store a fact
    client.post("/v1/facts",
        json={
            "project": "test",
            "content": "Test fact for debugging",
            "tags": ["debug"],
        },
        headers=auth_headers)

    # Recall and print 422 detail if it fails
    resp = client.get("/v1/projects/test/facts", headers=auth_headers)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 422:
        print("422 Detail:")
        print(json.dumps(resp.json(), indent=2))
    elif resp.status_code == 200:
        print("Success!")
        print(json.dumps(resp.json(), indent=2))
    else:
        print(f"Other Status: {resp.status_code}")
        print(resp.text)

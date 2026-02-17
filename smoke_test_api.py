import asyncio
import os
from cortex.api import app
from fastapi.testclient import TestClient

async def test():
    print("Starting lifespan...")
    test_db = "smoke_test.db"
    os.environ["CORTEX_DB"] = test_db
    
    with TestClient(app) as client:
        print("App is up!")
        resp = client.get("/health")
        print(f"Health: {resp.status_code}")
        print(resp.json())
    print("Lifespan ended.")

if __name__ == "__main__":
    asyncio.run(test())

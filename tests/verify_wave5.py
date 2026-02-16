import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path.cwd()))


async def verify_ledger_api():
    print("--- Verifying Ledger API & Metrics ---")
    from cortex.api import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # Check metrics
    response = client.get("/metrics")
    print(f"Metrics Status: {response.status_code}")
    if response.status_code == 200:
        print("✓ Metrics endpoint available")
        if "cortex_http_requests_total" in response.text:
            print("✓ Prometheus metrics being collected")

    # Check ledger status (requires auth, but we can check if route exists)
    # Since we can't easily bypass auth in a simple script without keys,
    # we just check if it's registered
    routes = [r.path for r in app.routes]
    if "/v1/ledger/status" in routes:
        print("✓ Ledger /status route registered")
    if "/v1/ledger/checkpoint" in routes:
        print("✓ Ledger /checkpoint route registered")


async def verify_mcp_v2():
    print("\n--- Verifying MCP v2 ---")
    try:
        from cortex.mcp_server_v2 import create_mcp_server, MCPServerConfig

        config = MCPServerConfig(db_path="~/.cortex/cortex_test.db")
        mcp = create_mcp_server(config)
        print("✓ MCP v2 server instance created successfully")
    except ImportError as e:
        print(f"✗ MCP v2 Verification failed: {e}")
    except Exception as e:
        print(f"✗ Unexpected error in MCP v2: {e}")


async def verify_sync_optimization():
    print("\n--- Verifying Sync Optimization ---")
    from cortex.engine import CortexEngine

    db_path = Path.home() / ".cortex" / "cortex_test_sync.db"
    if db_path.exists():
        db_path.unlink()

    engine = CortexEngine(db_path)
    # We just check if it runs without errors (mocking memory dir if needed)
    # For now, just a basic import and call check
    print("✓ Sync module imported and engine initialized")


async def main():
    await verify_ledger_api()
    await verify_mcp_v2()
    await verify_sync_optimization()
    print("\n--- Verification Complete ---")


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import sys

# Add swarm path to sys.path
sys.path.append("/Users/borjafernandezangulo/game/moskv-swarm")

from utils.cortex_bridge import CortexMemoryBridge


async def test_bridge():
    bridge = CortexMemoryBridge(base_url="http://localhost:8000")
    print(f"Connecting to {bridge.base_url}...")
    await bridge.connect()

    if bridge.is_connected:
        print("✅ Bridge CONNECTED")
        # Try a search
        results = await bridge.recall("Prime Directives")
        print(f"Found {len(results)} results for 'Prime Directives'")
        for fact in results:
            print(f"- [{fact.fact_type}] {fact.content[:100]}...")
    else:
        print("❌ Bridge CONNECTION FAILED")

    await bridge.close()


if __name__ == "__main__":
    asyncio.run(test_bridge())

import asyncio
import os
import sys

# Ensure we can import from local cortex
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cortex.async_client import AsyncCortexClient
from dotenv import load_dotenv

load_dotenv()

CODEX_PATH = "CODEX.md"


async def seed_codex():
    api_key = os.environ.get("CORTEX_API_KEY")
    # Force IPv4 to avoid [::1] connection refusal on macOS
    client = AsyncCortexClient(api_key=api_key, base_url="http://127.0.0.1:8000")

    # Wait for connection
    try:
        status = await client.status()
        print(f"🧠 Connected to CORTEX v{status.get('version')}")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return

    print("📜 Reading Codex...")
    with open(CODEX_PATH, "r") as f:
        content = f.read()

    # Split into sections (naive parsing)
    sections = content.split("## ")

    count = 0
    for section in sections:
        if not section.strip():
            continue

        lines = section.split("\n")
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()

        # Determine tags and type
        tags = ["codex", "ontology"]
        fact_type = "knowledge"

        if "Prime Directives" in title:
            fact_type = "axiom"
            tags.append("prime-directive")
        elif "Ontology" in title:
            fact_type = "schema"
            tags.append("fact-types")
        elif "Taxonomy" in title:
            fact_type = "schema"
            tags.append("taxonomy")
        elif "Protocols" in title:
            fact_type = "rule"
            tags.append("protocol")

        print(f"  > Seeding section: '{title}' ({fact_type})")

        await client.store(
            project="cortex", content=f"## {title}\n\n{body}", tags=tags, fact_type=fact_type
        )
        count += 1

    print(f"✨ Codex Seeded! ({count} sections stored)")
    await client.close()


if __name__ == "__main__":
    asyncio.run(seed_codex())

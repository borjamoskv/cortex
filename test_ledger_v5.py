import asyncio
import os
from cortex.engine import CortexEngine
from cortex.consensus.vote_ledger import ImmutableVoteLedger


async def test_ledger():
    db = os.path.expanduser("~/.cortex/cortex.db")
    print(f"Testing ledger on {db}")
    engine = CortexEngine(db)
    try:
        async with engine.session() as conn:
            print("Acquired connection")
            ledger = ImmutableVoteLedger(conn)
            print("Appending vote...")
            entry = await ledger.append_vote(fact_id=1, agent_id="tester", vote=1)
            print(f"Vote appended: {entry.hash[:16]}")

            print("Checking status...")
            async with conn.execute("SELECT COUNT(*) FROM vote_ledger") as cursor:
                count = (await cursor.fetchone())[0]
                print(f"Total votes: {count}")

            print("Verifying chain...")
            report = await ledger.verify_chain_integrity()
            print(f"Chain integrity: {report['valid']}")
    finally:
        await engine.close()
        print("Engine closed")


if __name__ == "__main__":
    asyncio.run(test_ledger())

import pytest
from cortex.engine import CortexEngine


@pytest.mark.asyncio
async def test_cdc_outbox_flow(tmp_path):
    db_path = str(tmp_path / "test_cdc.db")
    engine = CortexEngine(db_path=db_path)
    await engine.init_db()

    # 1. Store a fact
    fact_id = await engine.store(project="test", content="CDC Test Fact")

    # 2. Check outbox is empty
    conn = await engine.get_conn()
    async with conn.execute("SELECT COUNT(*) FROM graph_outbox") as cursor:
        row = await cursor.fetchone()
        assert row[0] == 0

    # 3. Deprecate fact
    await engine.deprecate(fact_id, reason="testing cdc")

    # 4. Check outbox has the event
    async with conn.execute("SELECT action, status, fact_id FROM graph_outbox") as cursor:
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "deprecate_fact"
        assert row[1] == "pending"
        assert row[2] == fact_id

    # 5. Process outbox
    # We expect this to return 0 if Neo4j is not running/configured
    processed = await engine.process_graph_outbox_async()
    assert processed == 0

    await engine.close()

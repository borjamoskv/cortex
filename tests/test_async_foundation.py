"""
Tests for Wave 5 Async Foundation.
Verifies CortexConnectionPool and AsyncCortexEngine.
"""

import asyncio
import os
import tempfile
import pytest
import aiosqlite

from cortex.connection_pool import CortexConnectionPool
from cortex.engine_async import AsyncCortexEngine
from cortex.exceptions import FactNotFound

from cortex.schema import ALL_SCHEMA

# Setup simplistic schema for testing
# We might need full schema in real scenarios, but for unit testing the pool
# and basic engine, we can use a subset or the real one if importable.


@pytest.fixture
async def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
async def pool(temp_db_path):
    pool = CortexConnectionPool(temp_db_path, min_connections=2, max_connections=4)

    # Initialize schema manually for tests
    async with aiosqlite.connect(temp_db_path) as conn:
        for stmt in ALL_SCHEMA:
            if "vec0" in stmt:
                continue  # Skip vector for now
            await conn.executescript(stmt)
        await conn.commit()

    await pool.initialize()
    yield pool
    await pool.close()


@pytest.fixture
async def engine(pool, temp_db_path):
    return AsyncCortexEngine(pool, temp_db_path, auto_embed=False)


@pytest.mark.asyncio
async def test_pool_initialization(pool):
    assert pool._initialized
    assert pool._active_count == 2  # Min connections


@pytest.mark.asyncio
async def test_pool_acquire_reuse(pool):
    async with pool.acquire() as conn1:
        assert isinstance(conn1, aiosqlite.Connection)
        # Should reuse one of the min connections
        assert pool._active_count == 2

    # After release, count should stay same (idle in pool)
    assert pool._active_count == 2


@pytest.mark.asyncio
async def test_pool_concurrency_limit(pool):
    # Retrieve max connections
    conns = []
    # pool max is 4

    # Acquire 4 connections
    for _ in range(4):
        ctx = pool.acquire()
        conn = await ctx.__aenter__()
        conns.append((ctx, conn))

    assert pool._active_count == 4

    # Next acquire should block or timeout
    try:
        async with asyncio.timeout(0.5):
            async with pool.acquire() as _:
                pytest.fail("Should have blocked")
    except asyncio.TimeoutError:
        pass

    # Release one
    ctx, conn = conns.pop()
    await ctx.__aexit__(None, None, None)

    # Now valid
    async with asyncio.timeout(1.0):
        async with pool.acquire() as _:
            pass  # Success

    # Cleanup
    for ctx, conn in conns:
        await ctx.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_engine_crud(engine):
    # Store
    fid = await engine.store("test-proj", "Hello Async World", fact_type="test")
    assert fid > 0

    # Retrieve
    fact = await engine.retrieve(fid)
    assert fact["content"] == "Hello Async World"
    assert fact["project"] == "test-proj"

    # Search
    results = await engine.search("Async", project="test-proj")
    assert len(results) == 1
    assert results[0].fact_id == fid

    # Delete
    assert await engine.delete_fact(fid)

    # Verify missing
    with pytest.raises(FactNotFound):
        await engine.retrieve(fid)

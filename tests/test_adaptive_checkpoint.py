"""Tests for CORTEX v4.1 — Adaptive Checkpointing.

Tests that the ledger dynamically adjusts batch size based on write rate.
"""

import time

import aiosqlite
import pytest

from cortex.config import CHECKPOINT_MAX, CHECKPOINT_MIN
from cortex.engine.ledger import ImmutableLedger


@pytest.fixture
async def ledger(tmp_path):
    """Create a temporary ledger wired to an in-memory DB."""
    from contextlib import asynccontextmanager

    db_path = str(tmp_path / "test_adaptive.db")
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row

    await conn.executescript("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash TEXT NOT NULL,
            prev_hash TEXT,
            project TEXT,
            content TEXT,
            fact_type TEXT DEFAULT 'knowledge',
            operation TEXT DEFAULT 'store',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS merkle_roots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            root_hash TEXT NOT NULL,
            tx_start_id INTEGER NOT NULL,
            tx_end_id INTEGER NOT NULL,
            tx_count INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    await conn.commit()

    # Mock pool that wraps the raw connection for ImmutableLedger's pool.acquire()
    class _MockPool:
        @asynccontextmanager
        async def acquire(self):
            yield conn

    ledger = ImmutableLedger(_MockPool())
    ledger._conn = conn  # Expose for tests that need direct DB access
    yield ledger
    await conn.close()


class TestAdaptiveBatchSize:
    """Tests for the adaptive_batch_size property."""

    @pytest.mark.asyncio
    async def test_default_batch_size(self, ledger):
        """With no writes, batch size should be at max."""
        assert ledger.adaptive_batch_size == CHECKPOINT_MAX

    @pytest.mark.asyncio
    async def test_batch_size_drops_under_high_load(self, ledger):
        """Simulate high write rate → batch size should drop to min."""
        now = time.monotonic()
        # Simulate 700 writes in the last 60 seconds (>10/sec)
        for i in range(700):
            ledger._write_timestamps.append(now - (i * 0.05))

        assert ledger.adaptive_batch_size == CHECKPOINT_MIN

    @pytest.mark.asyncio
    async def test_batch_size_recovers_after_calm(self, ledger):
        """Old timestamps outside the window → batch size returns to max."""
        old = time.monotonic() - 120  # 2 minutes ago (outside 60s window)
        for i in range(500):
            ledger._write_timestamps.append(old - i)

        assert ledger.adaptive_batch_size == CHECKPOINT_MAX

    @pytest.mark.asyncio
    async def test_record_write_tracks_timestamps(self, ledger):
        """record_write() should add a timestamp to the deque."""
        assert len(ledger._write_timestamps) == 0
        ledger.record_write()
        assert len(ledger._write_timestamps) == 1
        ledger.record_write()
        assert len(ledger._write_timestamps) == 2

    @pytest.mark.asyncio
    async def test_deque_maxlen_prevents_unbounded_growth(self, ledger):
        """Deque should not grow beyond maxlen."""
        for _ in range(6000):
            ledger.record_write()
        assert len(ledger._write_timestamps) == 5000  # maxlen

    @pytest.mark.asyncio
    async def test_legacy_class_attr_compat(self, ledger):
        """Legacy CHECKPOINT_BATCH_SIZE class attr should still be accessible."""
        assert ImmutableLedger.CHECKPOINT_BATCH_SIZE == CHECKPOINT_MAX


class TestCheckpointWithAdaptiveBatch:
    """Integration: verify checkpoint creation uses adaptive batch size."""

    @pytest.mark.asyncio
    async def test_checkpoint_not_created_below_threshold(self, ledger):
        """Checkpoint should not be created when pending < adaptive_batch_size."""
        # Insert 50 transactions (below both MIN and MAX thresholds)
        for i in range(50):
            await ledger._conn.execute(
                "INSERT INTO transactions (hash, prev_hash, project, content) VALUES (?, ?, ?, ?)",
                (f"hash_{i}", f"hash_{i - 1}" if i > 0 else None, "test", f"content_{i}"),
            )
        await ledger._conn.commit()

        result = await ledger.create_checkpoint_async()
        assert result is None

    @pytest.mark.asyncio
    async def test_checkpoint_created_at_min_threshold(self, ledger):
        """Under high write rate, checkpoint triggers at MIN batch size."""
        now = time.monotonic()
        for i in range(700):
            ledger._write_timestamps.append(now - (i * 0.05))

        assert ledger.adaptive_batch_size == CHECKPOINT_MIN

        # Insert exactly CHECKPOINT_MIN transactions
        for i in range(CHECKPOINT_MIN):
            await ledger._conn.execute(
                "INSERT INTO transactions (hash, prev_hash, project, content) VALUES (?, ?, ?, ?)",
                (f"hash_{i}", f"hash_{i - 1}" if i > 0 else None, "test", f"content_{i}"),
            )
        await ledger._conn.commit()

        result = await ledger.create_checkpoint_async()
        assert result is not None  # Checkpoint ID

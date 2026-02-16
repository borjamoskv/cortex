"""CORTEX Engine — Package init."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

import aiosqlite
import sqlite_vec

from cortex.config import DEFAULT_DB_PATH
from cortex.embeddings import LocalEmbedder
from cortex.engine.consensus_mixin import ConsensusMixin
from cortex.engine.models import Fact, row_to_fact
from cortex.engine.query_mixin import QueryMixin
from cortex.engine.store_mixin import StoreMixin
from cortex.engine.sync_compat import SyncCompatMixin
from cortex.metrics import metrics
from cortex.migrations.core import run_migrations, run_migrations_async
from cortex.schema import get_init_meta
from cortex.temporal import now_iso

logger = logging.getLogger("cortex")


from cortex.facts.manager import FactManager
from cortex.embeddings.manager import EmbeddingManager
from cortex.consensus.manager import ConsensusManager

class CortexEngine(SyncCompatMixin):
    """The Sovereign Ledger for AI Agents (Composite Orchestrator)."""

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        auto_embed: bool = True,
    ):
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._auto_embed = auto_embed
        self._conn: Optional[aiosqlite.Connection] = None
        self._vec_available = False
        self._conn_lock = asyncio.Lock()
        self._ledger = None  # Wave 5: ImmutableLedger (lazy init)
        
        # Composition layers
        self.facts = FactManager(self)
        self.embeddings = EmbeddingManager(self)
        self.consensus = ConsensusManager(self)

    # ─── Connection ───────────────────────────────────────────────

    async def get_conn(self) -> aiosqlite.Connection:
        """Returns the async database connection."""
        async with self._conn_lock:
            if self._conn is not None:
                return self._conn

            self._conn = await aiosqlite.connect(
                str(self._db_path), timeout=30
            )

            try:
                await self._conn.enable_load_extension(True)
                await self._conn.load_extension(sqlite_vec.loadable_path())
                await self._conn.enable_load_extension(False)
                self._vec_available = True
            except (OSError, AttributeError) as e:
                logger.debug("sqlite-vec extension not available: %s", e)
                self._vec_available = False

            await self._conn.execute("PRAGMA journal_mode=WAL")
            await self._conn.execute("PRAGMA synchronous=NORMAL")
            await self._conn.execute("PRAGMA foreign_keys=ON")
            return self._conn

    def _get_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
             raise RuntimeError("Connection not initialized. Call get_conn() first.")
        return self._conn

    # ─── Backward Compatibility Aliases & Delegation ──────────────

    async def store(self, *args, **kwargs):
        return await self.facts.store(*args, **kwargs)

    async def search(self, *args, **kwargs):
        return await self.facts.search(*args, **kwargs)

    async def recall(self, *args, **kwargs):
        return await self.facts.recall(*args, **kwargs)

    async def update(self, *args, **kwargs):
        return await self.facts.update(*args, **kwargs)

    async def deprecate(self, *args, **kwargs):
        return await self.facts.deprecate(*args, **kwargs)

    async def history(self, *args, **kwargs):
        return await self.facts.history(*args, **kwargs)

    async def vote(self, *args, **kwargs):
        return await self.consensus.vote(*args, **kwargs)

    async def stats(self):
        return await self.facts.stats()

    # ─── Schema ───────────────────────────────────────────────────

    async def init_db(self) -> None:
        """Initialize database schema. Safe to call multiple times."""
        from cortex.engine.ledger import ImmutableLedger
        from cortex.schema import ALL_SCHEMA

        conn = await self.get_conn()

        for stmt in ALL_SCHEMA:
            if "USING vec0" in stmt and not self._vec_available:
                continue
            await conn.executescript(stmt)
        await conn.commit()

        from cortex.migrations.core import run_migrations_async
        await run_migrations_async(conn)

        for k, v in get_init_meta():
            await conn.execute(
                "INSERT OR IGNORE INTO cortex_meta (key, value) VALUES (?, ?)",
                (k, v),
            )
        await conn.commit()

        self._ledger = ImmutableLedger(conn)
        metrics.set_engine(self)
        logger.info("CORTEX database initialized (async) at %s", self._db_path)

    # ─── Transaction Ledger ───────────────────────────────────────

    async def _log_transaction(self, conn, project, action, detail) -> int:
        from cortex.canonical import canonical_json, compute_tx_hash

        dj = canonical_json(detail)
        ts = now_iso()
        cursor = await conn.execute(
            "SELECT hash FROM transactions ORDER BY id DESC LIMIT 1"
        )
        prev = await cursor.fetchone()
        ph = prev[0] if prev else "GENESIS"
        th = compute_tx_hash(ph, project, action, dj, ts)
        
        c = await conn.execute(
            "INSERT INTO transactions "
            "(project, action, detail, prev_hash, hash, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (project, action, dj, ph, th, ts),
        )
        tx_id = c.lastrowid

        if self._ledger:
            try:
                self._ledger.record_write()
                await self._ledger.create_checkpoint_async()
            except Exception as e:
                logger.warning("Auto-checkpoint failed: %s", e)
                metrics.inc(
                    "cortex_ledger_checkpoint_failures_total",
                    meta={"error": str(e)},
                )

        return tx_id

    async def verify_ledger(self) -> dict:
        if not self._ledger:
            from cortex.engine.ledger import ImmutableLedger
            self._ledger = ImmutableLedger(await self.get_conn())
        return await self._ledger.verify_integrity_async()

    async def process_graph_outbox_async(self, limit: int = 10) -> int:
        from cortex.graph.backends.neo4j import Neo4jBackend
        conn = await self.get_conn()
        async with conn.execute(
            "SELECT id, fact_id, action FROM graph_outbox WHERE status = 'pending' LIMIT ?",
            (limit,),
        ) as cursor:
            events = await cursor.fetchall()
        
        if not events:
            return 0
            
        processed_count = 0
        try:
            neo4j = Neo4jBackend()
            if not neo4j._initialized:
                return 0
        except ImportError:
            return 0

        for event_id, fact_id, action in events:
            try:
                success = False
                if action == "deprecate_fact":
                    success = await neo4j.delete_fact_elements(fact_id)
                
                status = "processed" if success else "failed"
                await conn.execute(
                    "UPDATE graph_outbox SET status = ?, processed_at = ?, retry_count = retry_count + 1 WHERE id = ?",
                    (status, now_iso(), event_id),
                )
                processed_count += 1
            except Exception as e:
                logger.error("Failed to process CDC event %d: %s", event_id, e)
                await conn.execute(
                    "UPDATE graph_outbox SET status = 'failed', retry_count = retry_count + 1 WHERE id = ?",
                    (event_id,),
                )

        await conn.commit()
        return processed_count

    # ─── Helpers ──────────────────────────────────────────────────

    def export_snapshot(self, out_path: str | Path) -> str:
        from cortex.sync.snapshot import export_snapshot
        return export_snapshot(self, out_path)

    @staticmethod
    def _row_to_fact(row) -> Fact:
        return row_to_fact(row)

    # ─── Lifecycle ────────────────────────────────────────────────

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None
        self.close_sync()
        self._ledger = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

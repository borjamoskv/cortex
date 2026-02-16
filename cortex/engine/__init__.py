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
from cortex.migrations.core import run_migrations, run_migrations_async
from cortex.schema import get_init_meta
from cortex.temporal import now_iso

from cortex.engine.models import Fact, row_to_fact
from cortex.engine.store_mixin import StoreMixin
from cortex.metrics import metrics
from cortex.engine.query_mixin import QueryMixin
from cortex.engine.consensus_mixin import ConsensusMixin

logger = logging.getLogger("cortex")


class CortexEngine(StoreMixin, QueryMixin, ConsensusMixin):
    """The Sovereign Ledger for AI Agents."""

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        auto_embed: bool = True,
    ):
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._auto_embed = auto_embed
        self._embedder: Optional[LocalEmbedder] = None
        self._conn: Optional[aiosqlite.Connection] = None
        self._vec_available = False
        self._conn_lock = asyncio.Lock()
        self._ledger = None  # Wave 5: ImmutableLedger (lazy init)

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
                # Note: handle extension loading for aiosqlite
                await self._conn.enable_load_extension(True)
                # Use lower level load_extension if sqlite_vec.load fails on async
                # In Wave 5, we prioritize robust extension loading
                await self._conn.load_extension(sqlite_vec.loadable_path())
                await self._conn.enable_load_extension(False)
                self._vec_available = True
            except (OSError, AttributeError, Exception):
                self._vec_available = False

            await self._conn.execute("PRAGMA journal_mode=WAL")
            await self._conn.execute("PRAGMA synchronous=NORMAL")
            await self._conn.execute("PRAGMA foreign_keys=ON")
            return self._conn

    def _get_conn(self) -> aiosqlite.Connection:
        """Internal helper - WARNING: Use get_conn() wherever possible."""
        if self._conn is None:
             raise RuntimeError("Connection not initialized. Call get_conn() first.")
        return self._conn

    def get_connection(self) -> aiosqlite.Connection:
        """Public alias for backward compatibility. WARNING: Synchronous call to async resource."""
        return self._get_conn()

    # ─── Sync Compatibility Layer ─────────────────────────────────
    # Used by sync callers: cortex.sync.read, cortex.sync.write,
    # cortex.sync.common, CLI, etc.

    def _get_sync_conn(self):
        """Get a raw sqlite3.Connection for sync callers."""
        import sqlite3 as _sqlite3
        if not hasattr(self, "_sync_conn") or self._sync_conn is None:
            self._sync_conn = _sqlite3.connect(str(self._db_path), timeout=30)
            self._sync_conn.execute("PRAGMA journal_mode=WAL")
            self._sync_conn.execute("PRAGMA synchronous=NORMAL")
            self._sync_conn.execute("PRAGMA foreign_keys=ON")
            try:
                self._sync_conn.enable_load_extension(True)
                sqlite_vec.load(self._sync_conn)
                self._sync_conn.enable_load_extension(False)
            except (OSError, AttributeError, Exception):
                pass
        return self._sync_conn

    def init_db_sync(self) -> None:
        """Initialize database schema (sync version)."""
        from cortex.schema import ALL_SCHEMA
        conn = self._get_sync_conn()
        for stmt in ALL_SCHEMA:
            if "USING vec0" in stmt and not self._vec_available:
                continue
            conn.executescript(stmt)
        conn.commit()
        from cortex.migrations.core import run_migrations
        run_migrations(conn)
        for k, v in get_init_meta():
            conn.execute(
                "INSERT OR IGNORE INTO cortex_meta (key, value) VALUES (?, ?)",
                (k, v),
            )
        conn.commit()
        logger.info("CORTEX database initialized (sync) at %s", self._db_path)

    def store_sync(
        self,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags=None,
        confidence: str = "stated",
        source=None,
        meta=None,
        valid_from=None,
    ) -> int:
        """Store a fact synchronously (for sync callers like sync.read)."""
        import json as _json
        conn = self._get_sync_conn()
        ts = valid_from or now_iso()
        tags_json = _json.dumps(tags or [])
        meta_json = _json.dumps(meta or {})
        cursor = conn.execute(
            "INSERT INTO facts (project, content, fact_type, tags, confidence, "
            "valid_from, source, meta, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (project, content, fact_type, tags_json, confidence,
             ts, source, meta_json, ts, ts),
        )
        conn.commit()
        return cursor.lastrowid

    def close_sync(self):
        """Close sync connection."""
        if hasattr(self, "_sync_conn") and self._sync_conn:
            self._sync_conn.close()
            self._sync_conn = None

    def _get_embedder(self) -> LocalEmbedder:
        if self._embedder is None:
            self._embedder = LocalEmbedder()
        return self._embedder

    # ─── Schema ───────────────────────────────────────────────────

    async def init_db(self) -> None:
        """Initialize database schema. Safe to call multiple times."""
        from cortex.schema import ALL_SCHEMA
        from cortex.engine.ledger import ImmutableLedger

        conn = await self.get_conn()

        for stmt in ALL_SCHEMA:
            if "USING vec0" in stmt and not self._vec_available:
                continue
            await conn.executescript(stmt)
        await conn.commit()

        # run_migrations needs to be async too
        from cortex.migrations.core import run_migrations_async
        await run_migrations_async(conn)

        for k, v in get_init_meta():
            await conn.execute(
                "INSERT OR IGNORE INTO cortex_meta (key, value) VALUES (?, ?)",
                (k, v),
            )
        await conn.commit()

        # Wave 5: Initialize Immutable Ledger
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
        
        # Wave 5: Immutable Vote Ledger
        # If action is VOTE, we should ensure extra verification logic here
        
        c = await conn.execute(
            "INSERT INTO transactions "
            "(project, action, detail, prev_hash, hash, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (project, action, dj, ph, th, ts),
        )
        tx_id = c.lastrowid

        # Wave 5: Auto-checkpoint after threshold
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
        """Verify ledger integrity (hash chain + Merkle checkpoints)."""
        if not self._ledger:
            from cortex.engine.ledger import ImmutableLedger
            self._ledger = ImmutableLedger(await self.get_conn())
        return await self._ledger.verify_integrity_async()

    async def process_graph_outbox_async(self, limit: int = 10) -> int:
        """Process pending CDC events to sync Neo4j."""
        from cortex.graph import get_graph_async
        
        conn = await self.get_conn()
        async with conn.execute(
            "SELECT id, fact_id, action FROM graph_outbox WHERE status = 'pending' LIMIT ?",
            (limit,),
        ) as cursor:
            events = await cursor.fetchall()
        
        if not events:
            return 0
            
        processed_count = 0
        # For simplicity, we get the Neo4j backend via engine's graph interface
        # We assume Neo4j is configured if initialized
        try:
            from cortex.graph.backends.neo4j import Neo4jBackend
            neo4j = Neo4jBackend()
            if not neo4j._initialized:
                logger.debug("Neo4j not initialized, skipping outbox processing")
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

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

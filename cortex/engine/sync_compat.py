"""Sync compatibility mixin for CortexEngine.

Provides synchronous versions of core operations for CLI, sync callers,
and test utilities. Uses raw sqlite3 connections (not aiosqlite).
"""
from __future__ import annotations

import json
import logging
import sqlite3 as _sqlite3
from typing import Optional

import sqlite_vec

from cortex.temporal import now_iso
from cortex.engine.models import Fact

logger = logging.getLogger("cortex")


class SyncCompatMixin:
    """Synchronous compatibility layer for CortexEngine.

    These methods use a separate ``sqlite3.Connection`` (not aiosqlite)
    so they can be called from non-async contexts such as the CLI,
    ``cortex.sync.*`` modules, and test helpers.
    """

    # ─── Connection ─────────────────────────────────────────────

    def _get_sync_conn(self):
        """Get a raw sqlite3.Connection for sync callers."""
        if not hasattr(self, "_sync_conn") or self._sync_conn is None:
            self._sync_conn = _sqlite3.connect(
                str(self._db_path), timeout=30, check_same_thread=False,
            )
            self._sync_conn.execute("PRAGMA journal_mode=WAL")
            self._sync_conn.execute("PRAGMA synchronous=NORMAL")
            self._sync_conn.execute("PRAGMA foreign_keys=ON")
            try:
                self._sync_conn.enable_load_extension(True)
                sqlite_vec.load(self._sync_conn)
                self._sync_conn.enable_load_extension(False)
                self._vec_available = True
                logger.debug("sqlite-vec loaded successfully (sync)")
            except (OSError, AttributeError) as e:
                logger.debug("sqlite-vec extension not available (sync): %s", e)
                self._vec_available = False
        return self._sync_conn

    # ─── Init ───────────────────────────────────────────────────

    def init_db_sync(self) -> None:
        """Initialize database schema (sync version)."""
        from cortex.migrations.core import run_migrations
        from cortex.schema import ALL_SCHEMA

        conn = self._get_sync_conn()
        for stmt in ALL_SCHEMA:
            if "USING vec0" in stmt and not self._vec_available:
                continue
            conn.executescript(stmt)
        conn.commit()
        run_migrations(conn)
        from cortex.engine import get_init_meta
        for k, v in get_init_meta():
            conn.execute(
                "INSERT OR IGNORE INTO cortex_meta (key, value) VALUES (?, ?)",
                (k, v),
            )
        conn.commit()
        logger.info("CORTEX database initialized (sync) at %s", self._db_path)

    # ─── Store ──────────────────────────────────────────────────

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
        conn = self._get_sync_conn()
        ts = valid_from or now_iso()
        tags_json = json.dumps(tags or [])
        meta_json = json.dumps(meta or {})
        cursor = conn.execute(
            "INSERT INTO facts (project, content, fact_type, tags, confidence, "
            "valid_from, source, meta, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (project, content, fact_type, tags_json, confidence,
             ts, source, meta_json, ts, ts),
        )
        fact_id = cursor.lastrowid
        if self._auto_embed and self._vec_available:
            try:
                embedding = self._get_embedder().embed(content)
                conn.execute(
                    "INSERT INTO fact_embeddings (fact_id, embedding) "
                    "VALUES (?, ?)",
                    (fact_id, json.dumps(embedding)),
                )
            except Exception as e:
                logger.warning("Embedding failed for fact %d: %s", fact_id, e)
        conn.commit()

        # Graph extraction (sync)
        try:
            from cortex.graph import process_fact_graph_sync
            process_fact_graph_sync(conn, fact_id, content, project, ts)
        except Exception as e:
            logger.warning("Graph extraction sync failed for fact %d: %s", fact_id, e)

        return fact_id

    # ─── Search ─────────────────────────────────────────────────

    def search_sync(
        self,
        query: str,
        project: Optional[str] = None,
        top_k: int = 5,
    ) -> list:
        """Semantic vector search with text fallback (sync)."""
        from cortex.search_sync import (
            semantic_search_sync,
            text_search_sync,
        )

        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        conn = self._get_sync_conn()

        if self._vec_available:
            try:
                embedding = self._get_embedder().embed(query)
                results = semantic_search_sync(
                    conn, embedding, top_k=top_k, project=project,
                )
                if results:
                    return results
            except Exception as e:
                logger.warning("Semantic search sync failed: %s", e)

        return text_search_sync(conn, query, project=project, limit=top_k)

    def hybrid_search_sync(
        self,
        query: str,
        project: Optional[str] = None,
        top_k: int = 10,
        vector_weight: float = 0.6,
        text_weight: float = 0.4,
    ) -> list:
        """Hybrid search combining semantic + text via RRF (sync)."""
        from cortex.search_sync import hybrid_search_sync, text_search_sync

        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        conn = self._get_sync_conn()

        if not self._vec_available:
            return text_search_sync(conn, query, project=project, limit=top_k)

        embedding = self._get_embedder().embed(query)
        return hybrid_search_sync(
            conn, query, embedding,
            top_k=top_k, project=project,
            vector_weight=vector_weight,
            text_weight=text_weight,
        )

    # ─── Graph ──────────────────────────────────────────────────

    def graph_sync(self, project: Optional[str] = None, limit: int = 50) -> dict:
        """Retrieve the graph synchronously."""
        from cortex.graph.backends.sqlite import SQLiteBackend
        conn = self._get_sync_conn()
        return SQLiteBackend(conn).get_graph_sync(project=project, limit=limit)

    def query_entity_sync(self, name: str, project: Optional[str] = None) -> Optional[dict]:
        """Query an entity and its connections synchronously."""
        from cortex.graph.backends.sqlite import SQLiteBackend
        conn = self._get_sync_conn()
        return SQLiteBackend(conn).query_entity_sync(name=name, project=project)

    # ─── Consensus ──────────────────────────────────────────────

    def vote_sync(self, fact_id: int, agent: str, value: int) -> float:
        """Cast a v1 consensus vote synchronously.

        Args:
            fact_id: The fact to vote on.
            agent: Agent name.
            value: Vote value (-1, 0, or 1).

        Returns:
            Updated consensus score.
        """
        if value not in (-1, 0, 1):
            raise ValueError(f"vote value must be -1, 0, or 1, got {value}")
        conn = self._get_sync_conn()
        if value == 0:
            conn.execute(
                "DELETE FROM consensus_votes WHERE fact_id = ? AND agent = ?",
                (fact_id, agent),
            )
        else:
            conn.execute(
                "INSERT OR REPLACE INTO consensus_votes "
                "(fact_id, agent, vote) VALUES (?, ?, ?)",
                (fact_id, agent, value),
            )
        # Recalculate consensus score
        row = conn.execute(
            "SELECT SUM(vote) FROM consensus_votes WHERE fact_id = ?",
            (fact_id,),
        ).fetchone()
        vote_sum = row[0] or 0
        score = max(0.0, 1.0 + (vote_sum * 0.1))
        if score >= 1.5:
            conn.execute(
                "UPDATE facts SET consensus_score = ?, confidence = 'verified' "
                "WHERE id = ?",
                (score, fact_id),
            )
        elif score <= 0.5:
            conn.execute(
                "UPDATE facts SET consensus_score = ?, confidence = 'disputed' "
                "WHERE id = ?",
                (score, fact_id),
            )
        else:
            conn.execute(
                "UPDATE facts SET consensus_score = ? WHERE id = ?",
                (score, fact_id),
            )
        conn.commit()
        return score

    # ─── Ledger (Sync) ──────────────────────────────────────────

    def _log_transaction_sync(self, conn, project, action, detail) -> int:
        """Synchronous version of _log_transaction."""
        from cortex.canonical import canonical_json, compute_tx_hash

        dj = canonical_json(detail)
        ts = now_iso()
        cursor = conn.execute(
            "SELECT hash FROM transactions ORDER BY id DESC LIMIT 1"
        )
        prev = cursor.fetchone()
        ph = prev[0] if prev else "GENESIS"
        th = compute_tx_hash(ph, project, action, dj, ts)
        
        c = conn.execute(
            "INSERT INTO transactions "
            "(project, action, detail, prev_hash, hash, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (project, action, dj, ph, th, ts),
        )
        tx_id = c.lastrowid
        
        # Note: Auto-checkpoint is skipped in sync mode for now to avoid complexity
        return tx_id

    def deprecate_sync(self, fact_id: int, reason: Optional[str] = None) -> bool:
        """Synchronous version of deprecate."""
        if not isinstance(fact_id, int) or fact_id <= 0:
            raise ValueError("Invalid fact_id")
        
        conn = self._get_sync_conn()
        ts = now_iso()
        cursor = conn.execute(
            "UPDATE facts SET valid_until = ?, updated_at = ?, "
            "meta = json_set(COALESCE(meta, '{}'), '$.deprecation_reason', ?) "
            "WHERE id = ? AND valid_until IS NULL",
            (ts, ts, reason or "deprecated", fact_id),
        )

        if cursor.rowcount > 0:
            cursor = conn.execute(
                "SELECT project FROM facts WHERE id = ?", (fact_id,)
            )
            row = cursor.fetchone()
            self._log_transaction_sync(
                conn,
                row[0] if row else "unknown",
                "deprecate",
                {"fact_id": fact_id, "reason": reason},
            )
            # CDC: Encole for Neo4j sync (table graph_outbox)
            conn.execute(
                "INSERT INTO graph_outbox (fact_id, action, status) VALUES (?, ?, ?)",
                (fact_id, "deprecate_fact", "pending")
            )
            conn.commit()
            return True
        return False

    def recall_sync(
        self,
        project: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[Fact]:
        """Synchronous version of recall."""
        from cortex.engine.query_mixin import _FACT_COLUMNS, _FACT_JOIN

        conn = self._get_sync_conn()
        query = f"""
            SELECT {_FACT_COLUMNS}
            {_FACT_JOIN}
            WHERE f.project = ? AND f.valid_until IS NULL
            ORDER BY (
                f.consensus_score * 0.8
                + (1.0 / (1.0 + (julianday('now') - julianday(f.created_at)))) * 0.2
            ) DESC, f.fact_type, f.created_at DESC
        """
        params: list = [project]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        if offset:
            query += " OFFSET ?"
            params.append(offset)
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        return [self._row_to_fact(row) for row in rows]

    def history_sync(
        self,
        project: str,
        as_of: Optional[str] = None,
    ) -> list[Fact]:
        """Synchronous version of history."""
        from cortex.engine.query_mixin import _FACT_COLUMNS, _FACT_JOIN
        from cortex.temporal import build_temporal_filter_params

        conn = self._get_sync_conn()
        if as_of:
            clause, params = build_temporal_filter_params(as_of, table_alias="f")
            query = (
                f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} "
                f"WHERE f.project = ? AND {clause} "
                "ORDER BY f.valid_from DESC"
            )
            cursor = conn.execute(query, [project] + params)
        else:
            query = (
                f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} "
                "WHERE f.project = ? "
                "ORDER BY f.valid_from DESC"
            )
            cursor = conn.execute(query, (project,))
        
        rows = cursor.fetchall()
        return [self._row_to_fact(row) for row in rows]

    def stats_sync(self) -> dict:
        """Synchronous version of stats."""
        conn = self._get_sync_conn()
        
        cursor = conn.execute("SELECT COUNT(*) FROM facts")
        total = cursor.fetchone()[0]

        cursor = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE valid_until IS NULL"
        )
        active = cursor.fetchone()[0]

        cursor = conn.execute(
            "SELECT DISTINCT project FROM facts WHERE valid_until IS NULL"
        )
        projects = [p[0] for p in cursor.fetchall()]

        cursor = conn.execute(
            "SELECT fact_type, COUNT(*) "
            "FROM facts WHERE valid_until IS NULL "
            "GROUP BY fact_type"
        )
        types = dict(cursor.fetchall())

        cursor = conn.execute("SELECT COUNT(*) FROM transactions")
        tx_count = cursor.fetchone()[0]

        db_size = (
            self._db_path.stat().st_size / (1024 * 1024)
            if self._db_path.exists()
            else 0
        )

        try:
            cursor = conn.execute("SELECT COUNT(*) FROM fact_embeddings")
            embeddings = cursor.fetchone()[0]
        except Exception:
            embeddings = 0

        return {
            "total_facts": total,
            "active_facts": active,
            "deprecated_facts": total - active,
            "projects": projects,
            "project_count": len(projects),
            "types": types,
            "transactions": tx_count,
            "embeddings": embeddings,
            "db_path": str(self._db_path),
            "db_size_mb": round(db_size, 2),
        }

    def register_ghost_sync(
        self, reference: str, context: str, project: str
    ) -> int:
        """Register a ghost synchronously."""
        conn = self._get_sync_conn()
        cursor = conn.execute(
            "SELECT id FROM ghosts WHERE reference = ? AND project = ?",
            (reference, project),
        )
        row = cursor.fetchone()
        if row:
            return row[0]

        ts = now_iso()
        cursor = conn.execute(
            "INSERT INTO ghosts "
            "(reference, context, project, status, created_at) "
            "VALUES (?, ?, ?, 'open', ?)",
            (reference, context, project, ts),
        )
        ghost_id = cursor.lastrowid
        conn.commit()
        return ghost_id

    def resolve_ghost_sync(
        self, ghost_id: int, target_entity_id: int, confidence: float = 1.0
    ) -> bool:
        """Resolve a ghost synchronously."""
        conn = self._get_sync_conn()
        ts = now_iso()
        cursor = conn.execute(
            "UPDATE ghosts SET status = 'resolved', target_id = ?, "
            "confidence = ?, resolved_at = ? WHERE id = ?",
            (target_entity_id, confidence, ts, ghost_id),
        )
        conn.commit()
        return cursor.rowcount > 0

    # ─── Cleanup ────────────────────────────────────────────────

    def close_sync(self):
        """Close sync connection."""
        if hasattr(self, "_sync_conn") and self._sync_conn:
            self._sync_conn.close()
            self._sync_conn = None

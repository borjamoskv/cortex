"""Sync write mixin for CortexEngine.

Provides synchronous write operations (store, vote, ghosts, migrations).
"""

from __future__ import annotations

import json
import logging
import hashlib
from typing import Any

from cortex.temporal import now_iso
from cortex.sync.gitops import sync_fact_to_repo

logger = logging.getLogger("cortex")


class SyncWriteMixin:
    """Mixin for synchronous write operations."""

    def init_db_sync(self) -> None:
        """Initialize database schema (sync version)."""
        from cortex.migrations.core import run_migrations
        from cortex.schema import ALL_SCHEMA
        from cortex.engine import get_init_meta

        conn = self._get_sync_conn()
        for stmt in ALL_SCHEMA:
            if "USING vec0" in stmt and not self._vec_available:
                continue
            conn.executescript(stmt)
        conn.commit()
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
        if not project or not project.strip():
            raise ValueError("project cannot be empty")
        if not content or not content.strip():
            raise ValueError("content cannot be empty")

        conn = self._get_sync_conn()
        ts = valid_from or now_iso()
        tags_json = json.dumps(tags or [])
        meta_json = json.dumps(meta or {})
        cursor = conn.execute(
            "INSERT INTO facts (project, content, fact_type, tags, confidence, "
            "valid_from, source, meta, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (project, content, fact_type, tags_json, confidence, ts, source, meta_json, ts, ts),
        )
        fact_id = cursor.lastrowid
        if self._auto_embed and self._vec_available:
            try:
                embedding = self._get_embedder().embed(content)
                conn.execute(
                    "INSERT INTO fact_embeddings (fact_id, embedding) VALUES (?, ?)",
                    (fact_id, json.dumps(embedding)),
                )
            except Exception as e:
                logger.warning("Embedding failed for fact %d: %s", fact_id, e)
        conn.commit()

        # Log to ledger (sync)
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        self._log_transaction_sync(
            conn, project, "store", {"fact_id": fact_id, "content_hash": content_hash}
        )

        # CDC: Encole for Neo4j sync
        conn.execute(
            "INSERT INTO graph_outbox (fact_id, action, status) VALUES (?, ?, ?)",
            (fact_id, "store_fact", "pending"),
        )
        conn.commit()

        # Graph extraction (sync)
        try:
            from cortex.graph import process_fact_graph_sync

            process_fact_graph_sync(conn, fact_id, content, project, ts)
        except Exception as e:
            logger.warning("Graph extraction sync failed for fact %d: %s", fact_id, e)

        # [GitOps Sync]
        fact_data = {
            "id": fact_id,
            "project": project,
            "content": content,
            "fact_type": fact_type,
            "tags": tags or [],
            "confidence": confidence,
            "source": source,
            "meta": meta or {},
            "created_at": ts,
            "valid_from": ts
        }
        try:
            sync_fact_to_repo(project, fact_id, fact_data, "upsert")
        except Exception as e:
            logger.warning("GitOps sync falló para fact %d: %s", fact_id, e)

        return fact_id

    def vote_sync(self, fact_id: int, agent: str, value: int) -> float:
        """Cast a v1 consensus vote synchronously."""
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
                "INSERT OR REPLACE INTO consensus_votes (fact_id, agent, vote) VALUES (?, ?, ?)",
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
                "UPDATE facts SET consensus_score = ?, confidence = 'verified' WHERE id = ?",
                (score, fact_id),
            )
        elif score <= 0.5:
            conn.execute(
                "UPDATE facts SET consensus_score = ?, confidence = 'disputed' WHERE id = ?",
                (score, fact_id),
            )
        else:
            conn.execute(
                "UPDATE facts SET consensus_score = ? WHERE id = ?",
                (score, fact_id),
            )
        conn.commit()
        return score

    def _log_transaction_sync(self, conn, project, action, detail) -> int:
        """Synchronous version of _log_transaction."""
        from cortex.canonical import canonical_json, compute_tx_hash

        dj = canonical_json(detail)
        ts = now_iso()
        cursor = conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1")
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
        return tx_id

    def deprecate_sync(self, fact_id: int, reason: str | None = None) -> bool:
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
            cursor = conn.execute("SELECT project FROM facts WHERE id = ?", (fact_id,))
            row = cursor.fetchone()
            self._log_transaction_sync(
                conn,
                row[0] if row else "unknown",
                "deprecate",
                {"fact_id": fact_id, "reason": reason},
            )
            # CDC: Encole for Neo4j sync
            conn.execute(
                "INSERT INTO graph_outbox (fact_id, action, status) VALUES (?, ?, ?)",
                (fact_id, "deprecate_fact", "pending"),
            )
            conn.commit()
            
            # [GitOps Sync]
            try:
                sync_fact_to_repo(
                    row[0] if row else "unknown",
                    fact_id,
                    {"id": fact_id, "valid_until": ts, "meta": {"deprecation_reason": reason or "deprecated"}},
                    "deprecate"
                )
            except Exception as e:
                logger.warning("GitOps sync falló para fact %d: %s", fact_id, e)
                
            return True
        return False

    def register_ghost_sync(self, reference: str, context: str, project: str) -> int:
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

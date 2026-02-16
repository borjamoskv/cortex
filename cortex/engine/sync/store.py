"""Sync Store/Query module for CORTEX."""

from __future__ import annotations

import json
import logging
from typing import Optional
from cortex.temporal import now_iso, build_temporal_filter_params
from cortex.engine.models import Fact

logger = logging.getLogger("cortex.engine.sync.store")


class SyncStoreMixin:
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
        """Store a fact synchronously."""
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
                embedding = self.embeddings._get_embedder().embed(content)
                conn.execute(
                    "INSERT INTO fact_embeddings (fact_id, embedding) VALUES (?, ?)",
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
            cursor = conn.execute("SELECT project FROM facts WHERE id = ?", (fact_id,))
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
                (fact_id, "deprecate_fact", "pending"),
            )
            conn.commit()
            return True
        return False

    def stats_sync(self) -> dict:
        """Synchronous version of stats."""
        conn = self._get_sync_conn()

        cursor = conn.execute("SELECT COUNT(*) FROM facts")
        total = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM facts WHERE valid_until IS NULL")
        active = cursor.fetchone()[0]

        cursor = conn.execute("SELECT DISTINCT project FROM facts WHERE valid_until IS NULL")
        projects = [p[0] for p in cursor.fetchall()]

        cursor = conn.execute(
            "SELECT fact_type, COUNT(*) FROM facts WHERE valid_until IS NULL GROUP BY fact_type"
        )
        types = dict(cursor.fetchall())

        cursor = conn.execute("SELECT COUNT(*) FROM transactions")
        tx_count = cursor.fetchone()[0]

        db_size = self._db_path.stat().st_size / (1024 * 1024) if self._db_path.exists() else 0

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

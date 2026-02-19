"""Sync read mixin for CortexEngine.

Provides synchronous read operations (search, graph, history, stats).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from cortex.engine.models import Fact

logger = logging.getLogger("cortex")


class SyncReadMixin:
    """Mixin for synchronous read operations."""

    def search_sync(
        self,
        query: str,
        project: str | None = None,
        top_k: int = 5,
    ) -> list:
        """Semantic vector search with text fallback (sync)."""
        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        from cortex.search_sync import (
            semantic_search_sync,
            text_search_sync,
        )

        conn = self._get_sync_conn()

        if self._vec_available:
            try:
                embedding = self._get_embedder().embed(query)
                results = semantic_search_sync(
                    conn,
                    embedding,
                    top_k=top_k,
                    project=project,
                )
                if results:
                    return results
            except Exception as e:
                logger.warning("Semantic search sync failed: %s", e)

        return text_search_sync(conn, query, project=project, limit=top_k)

    def hybrid_search_sync(
        self,
        query: str,
        project: str | None = None,
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
            conn,
            query,
            embedding,
            top_k=top_k,
            project=project,
            vector_weight=vector_weight,
            text_weight=text_weight,
        )

    def graph_sync(self, project: str | None = None, limit: int = 50) -> dict:
        """Retrieve the graph synchronously."""
        from cortex.graph.backends.sqlite import SQLiteBackend

        conn = self._get_sync_conn()
        return SQLiteBackend(conn).get_graph_sync(project=project, limit=limit)

    def query_entity_sync(self, name: str, project: str | None = None) -> dict | None:
        """Query an entity and its connections synchronously."""
        from cortex.graph.backends.sqlite import SQLiteBackend

        conn = self._get_sync_conn()
        return SQLiteBackend(conn).query_entity_sync(name=name, project=project)

    def recall_sync(
        self,
        project: str,
        limit: int | None = None,
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

    def reconstruct_state_sync(
        self,
        target_tx_id: int,
        project: str | None = None,
    ) -> list[Fact]:
        """Synchronous version of reconstruct_state."""
        from cortex.engine.query_mixin import _FACT_COLUMNS, _FACT_JOIN

        conn = self._get_sync_conn()
        cursor = conn.execute(
            "SELECT timestamp FROM transactions WHERE id = ?",
            (target_tx_id,),
        )
        tx = cursor.fetchone()
        if not tx:
            raise ValueError(f"Transaction {target_tx_id} not found")
        tx_time = tx[0]

        query = (
            f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} "
            "WHERE (f.created_at <= ? "
            "  AND (f.valid_until IS NULL OR f.valid_until > ?)) "
            "  AND (f.tx_id IS NULL OR f.tx_id <= ?)"
        )
        params: list = [tx_time, tx_time, target_tx_id]
        if project:
            query += " AND f.project = ?"
            params.append(project)
        query += " ORDER BY f.id ASC"
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        return [self._row_to_fact(row) for row in rows]

    def history_sync(
        self,
        project: str,
        as_of: str | None = None,
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

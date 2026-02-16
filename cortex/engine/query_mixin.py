"""Query mixin — search, recall, history, reconstruct_state, stats."""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Optional

from cortex.engine.models import Fact, row_to_fact
from cortex.search import SearchResult, semantic_search, text_search
from cortex.temporal import build_temporal_filter_params, now_iso

logger = logging.getLogger("cortex")


class QueryMixin:
    """Mixin providing query/search methods for CortexEngine."""

    def search(
        self,
        query: str,
        project: Optional[str] = None,
        top_k: int = 5,
        as_of: Optional[str] = None,
        **kwargs,
    ) -> list[SearchResult]:
        """Semantic search across facts."""
        if not query or not query.strip():
            raise ValueError("query cannot be empty")
        conn = self._get_conn()
        try:
            embedder = self._get_embedder()
            query_embedding = embedder.embed(query)
            results = semantic_search(conn, query_embedding, top_k, project, as_of)
            if results:
                return results
        except (ValueError, RuntimeError, sqlite3.Error) as e:
            logger.warning("Semantic search failed, falling back to text: %s", e)
        return text_search(
            conn, query, project, limit=top_k,
            fact_type=kwargs.get("fact_type"), tags=kwargs.get("tags"),
        )

    def recall(
        self,
        project: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[Fact]:
        """Load all active facts for a project."""
        conn = self._get_conn()
        query = """
            SELECT f.id, f.project, f.content, f.fact_type, f.tags, f.confidence,
                   f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score,
                   f.created_at, f.updated_at, f.tx_id, t.hash
            FROM facts f
            LEFT JOIN transactions t ON f.tx_id = t.id
            WHERE f.project = ? AND f.valid_until IS NULL
            ORDER BY
                (f.consensus_score * 0.8 + (1.0 / (1.0 + (julianday('now') - julianday(f.created_at)))) * 0.2) DESC,
                f.fact_type, f.created_at DESC
        """
        params = [project]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        if offset:
            query += " OFFSET ?"
            params.append(offset)
        cursor = conn.execute(query, params)
        return [self._row_to_fact(row) for row in cursor.fetchall()]

    def _verify_fact_tenant(self, fact_id: int, tenant_id: str) -> bool:
        """Lightweight check for fact tenant ownership."""
        conn = self._get_conn()
        row = conn.execute("SELECT project FROM facts WHERE id = ?", (fact_id,)).fetchone()
        return row is not None and row[0] == tenant_id

    def history(self, project: str, as_of: Optional[str] = None) -> list[Fact]:
        """Get facts as they were at a specific point in time."""
        conn = self._get_conn()
        if as_of:
            clause, params = build_temporal_filter_params(as_of, table_alias="f")
            query = """
                SELECT f.id, f.project, f.content, f.fact_type, f.tags, f.confidence,
                       f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score,
                       f.created_at, f.updated_at, f.tx_id, t.hash
                FROM facts f
                LEFT JOIN transactions t ON f.tx_id = t.id
                WHERE f.project = ? AND """ + clause + """
                ORDER BY f.valid_from DESC
                """
            cursor = conn.execute(query, [project] + params)
        else:
            cursor = conn.execute(
                """
                SELECT f.id, f.project, f.content, f.fact_type, f.tags, f.confidence,
                       f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score,
                       f.created_at, f.updated_at, f.tx_id, t.hash
                FROM facts f
                LEFT JOIN transactions t ON f.tx_id = t.id
                WHERE f.project = ?
                ORDER BY f.valid_from DESC
                """,
                (project,),
            )
        return [self._row_to_fact(row) for row in cursor.fetchall()]

    def reconstruct_state(self, target_tx_id: int, project: Optional[str] = None) -> list[Fact]:
        """Reconstruct the active database state at a specific transaction ID."""
        conn = self._get_conn()
        tx = conn.execute("SELECT timestamp FROM transactions WHERE id = ?", (target_tx_id,)).fetchone()
        if not tx:
            raise ValueError(f"Transaction ID {target_tx_id} not found")
        tx_time = tx[0]
        query = """
            SELECT f.id, f.project, f.content, f.fact_type, f.tags, f.confidence,
                   f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score,
                   f.created_at, f.updated_at, f.tx_id, t.hash
            FROM facts f
            LEFT JOIN transactions t ON f.tx_id = t.id
            WHERE (f.created_at <= ? AND (f.valid_until IS NULL OR f.valid_until > ?))
              AND (f.tx_id IS NULL OR f.tx_id <= ?)
        """
        params = [tx_time, tx_time, target_tx_id]
        if project:
            query += " AND f.project = ?"
            params.append(project)
        query += " ORDER BY id ASC"
        cursor = conn.execute(query, params)
        return [self._row_to_fact(row) for row in cursor.fetchall()]

    def stats(self) -> dict:
        """Get database statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM facts WHERE valid_until IS NULL").fetchone()[0]
        deprecated = total - active
        projects = conn.execute("SELECT DISTINCT project FROM facts WHERE valid_until IS NULL").fetchall()
        project_list = [p[0] for p in projects]
        types = conn.execute(
            "SELECT fact_type, COUNT(*) FROM facts WHERE valid_until IS NULL GROUP BY fact_type"
        ).fetchall()
        if self._vec_available:
            embeddings = conn.execute("SELECT COUNT(*) FROM fact_embeddings").fetchone()[0]
        else:
            embeddings = 0
        transactions = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        return {
            "total_facts": total, "active_facts": active,
            "deprecated_facts": deprecated, "projects": project_list,
            "project_count": len(project_list),
            "types": {t: c for t, c in types},
            "embeddings": embeddings, "transactions": transactions,
            "db_path": str(self._db_path),
            "db_size_mb": round(self._db_path.stat().st_size / 1_048_576, 2)
            if self._db_path.exists() else 0,
        }

""" Query mixin — search, recall, history, reconstruct_state, stats. """
from __future__ import annotations
import json
import logging
from typing import Optional
from cortex.engine.models import Fact
from cortex.search import SearchResult, semantic_search, text_search
from cortex.temporal import build_temporal_filter_params, now_iso, time_travel_filter

logger = logging.getLogger("cortex")

class QueryMixin:
    async def search(self, query: str, project: Optional[str] = None, top_k: int = 5, as_of: Optional[str] = None, **kwargs) -> list[SearchResult]:
        if not query or not query.strip(): raise ValueError("query cannot be empty")
        conn = await self.get_conn()
        try:
            results = await semantic_search(conn, self._get_embedder().embed(query), top_k, project, as_of)
            if results: return results
        except Exception as e:
            logger.warning("Semantic search failed: %s", e)
        return await text_search(conn, query, project, limit=top_k, **kwargs)

    async def recall(self, project: str, limit: Optional[int] = None, offset: int = 0) -> list[Fact]:
        conn = await self.get_conn()
        query = """
            SELECT f.id, f.project, f.content, f.fact_type, f.tags, f.confidence,
                   f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score,
                   f.created_at, f.updated_at, f.tx_id, t.hash
            FROM facts f LEFT JOIN transactions t ON f.tx_id = t.id
            WHERE f.project = ? AND f.valid_until IS NULL
            ORDER BY (f.consensus_score * 0.8 + (1.0 / (1.0 + (julianday('now') - julianday(f.created_at)))) * 0.2) DESC, f.fact_type, f.created_at DESC
        """
        params = [project]
        if limit: query += " LIMIT ?"; params.append(limit)
        if offset: query += " OFFSET ?"; params.append(offset)
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [self._row_to_fact(row) for row in rows]

    async def history(self, project: str, as_of: Optional[str] = None) -> list[Fact]:
        conn = await self.get_conn()
        if as_of:
            clause, params = build_temporal_filter_params(as_of, table_alias="f")
            query = f"SELECT f.id, f.project, f.content, f.fact_type, f.tags, f.confidence, f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score, f.created_at, f.updated_at, f.tx_id, t.hash FROM facts f LEFT JOIN transactions t ON f.tx_id = t.id WHERE f.project = ? AND {clause} ORDER BY f.valid_from DESC"
            cursor = await conn.execute(query, [project] + params)
        else:
            cursor = await conn.execute("SELECT f.id, f.project, f.content, f.fact_type, f.tags, f.confidence, f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score, f.created_at, f.updated_at, f.tx_id, t.hash FROM facts f LEFT JOIN transactions t ON f.tx_id = t.id WHERE f.project = ? ORDER BY f.valid_from DESC", (project,))
        rows = await cursor.fetchall()
        return [self._row_to_fact(row) for row in rows]

    async def reconstruct_state(self, target_tx_id: int, project: Optional[str] = None) -> list[Fact]:
        conn = await self.get_conn()
        cursor = await conn.execute("SELECT timestamp FROM transactions WHERE id = ?", (target_tx_id,))
        tx = await cursor.fetchone()
        if not tx: raise ValueError(f"Transaction {target_tx_id} not found")
        tx_time = tx[0]
        query = "SELECT f.id, f.project, f.content, f.fact_type, f.tags, f.confidence, f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score, f.created_at, f.updated_at, f.tx_id, t.hash FROM facts f LEFT JOIN transactions t ON f.tx_id = t.id WHERE (f.created_at <= ? AND (f.valid_until IS NULL OR f.valid_until > ?)) AND (f.tx_id IS NULL OR f.tx_id <= ?)"
        params = [tx_time, tx_time, target_tx_id]
        if project: query += " AND f.project = ?"; params.append(project)
        query += " ORDER BY f.id ASC"
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [self._row_to_fact(row) for row in rows]

    async def time_travel(self, tx_id: int, project: str | None = None) -> list[Fact]:
        """Reconstruct fact state at a historical transaction point.

        More precise than ``reconstruct_state``: uses ``time_travel_filter``
        which correlates ``tx_id`` ordering with ``valid_until`` timestamps
        pulled from the transaction ledger.

        Args:
            tx_id: Transaction ID to travel to.
            project: Optional project filter.

        Returns:
            List of facts that were active at that transaction.
        """
        conn = await self.get_conn()
        clause, params = time_travel_filter(tx_id, table_alias="f")
        query = (
            "SELECT f.id, f.project, f.content, f.fact_type, f.tags, "
            "f.confidence, f.valid_from, f.valid_until, f.source, f.meta, "
            "f.consensus_score, f.created_at, f.updated_at, f.tx_id, t.hash "
            "FROM facts f LEFT JOIN transactions t ON f.tx_id = t.id "
            f"WHERE {clause}"
        )
        if project:
            query += " AND f.project = ?"
            params.append(project)
        query += " ORDER BY f.id ASC"
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [self._row_to_fact(row) for row in rows]

    async def stats(self) -> dict:
        conn = await self.get_conn()
        cursor = await conn.execute("SELECT COUNT(*) FROM facts")
        total = (await cursor.fetchone())[0]
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM facts WHERE valid_until IS NULL"
        )
        active = (await cursor.fetchone())[0]
        cursor = await conn.execute(
            "SELECT DISTINCT project FROM facts WHERE valid_until IS NULL"
        )
        projects = [p[0] for p in await cursor.fetchall()]
        cursor = await conn.execute(
            "SELECT fact_type, COUNT(*) FROM facts WHERE valid_until IS NULL GROUP BY fact_type"
        )
        types = {t: c for t, c in await cursor.fetchall()}
        cursor = await conn.execute("SELECT COUNT(*) FROM transactions")
        tx_count = (await cursor.fetchone())[0]
        
        db_size = (
            self._db_path.stat().st_size / (1024 * 1024)
            if self._db_path.exists()
            else 0
        )

        try:
            cursor = await conn.execute("SELECT COUNT(*) FROM fact_embeddings")
            embeddings = (await cursor.fetchone())[0]
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

    async def graph(self, project: Optional[str] = None):
        from cortex.graph import get_graph
        conn = await self.get_conn()
        return get_graph(conn, project)

    async def query_entity(self, name: str, project: Optional[str] = None) -> list[dict]:
        from cortex.graph import query_entity
        conn = await self.get_conn()
        return query_entity(conn, name, project)


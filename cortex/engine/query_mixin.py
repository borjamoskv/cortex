"""Query mixin — search, recall, history, reconstruct_state, stats."""

from __future__ import annotations

import logging
from typing import Optional

from cortex.engine.models import Fact
from cortex.search import SearchResult, semantic_search, text_search
from cortex.temporal import build_temporal_filter_params, time_travel_filter

logger = logging.getLogger("cortex")

# Common column list shared across all fact queries.
_FACT_COLUMNS = (
    "f.id, f.project, f.content, f.fact_type, f.tags, f.confidence, "
    "f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score, "
    "f.created_at, f.updated_at, f.tx_id, t.hash"
)
_FACT_JOIN = "FROM facts f LEFT JOIN transactions t ON f.tx_id = t.id"


class QueryMixin:
    async def search(
        self,
        query: str,
        project: Optional[str] = None,
        graph_depth: int = 0,
        **kwargs,
    ) -> list[SearchResult]:
        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        from cortex.graph import extract_entities, get_context_subgraph

        async with self.session() as conn:
            results = []
            try:
                results = await semantic_search(
                    conn,
                    self._get_embedder().embed(query),
                    top_k,
                    project,
                    as_of,
                )
            except Exception as e:
                logger.warning("Semantic search failed: %s", e)
            
            if not results:
                results = await text_search(conn, query, project, limit=top_k, **kwargs)

            if results and graph_depth > 0:
                for res in results:
                    entities = extract_entities(res.content)
                    seeds = [e["name"] for e in entities]
                    if seeds:
                        res.graph_context = await get_context_subgraph(conn, seeds, depth=graph_depth)

            return results

    async def recall(
        self,
        project: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[Fact]:
        async with self.session() as conn:
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
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [self._row_to_fact(row) for row in rows]

    async def history(
        self,
        project: str,
        as_of: Optional[str] = None,
    ) -> list[Fact]:
        async with self.session() as conn:
            if as_of:
                clause, params = build_temporal_filter_params(as_of, table_alias="f")
                query = (
                    f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} "
                    f"WHERE f.project = ? AND {clause} "
                    "ORDER BY f.valid_from DESC"
                )
                cursor = await conn.execute(query, [project] + params)
            else:
                query = (
                    f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} "
                    "WHERE f.project = ? "
                    "ORDER BY f.valid_from DESC"
                )
                cursor = await conn.execute(query, (project,))
            rows = await cursor.fetchall()
            return [self._row_to_fact(row) for row in rows]

    async def reconstruct_state(
        self,
        target_tx_id: int,
        project: Optional[str] = None,
    ) -> list[Fact]:
        async with self.session() as conn:
            cursor = await conn.execute(
                "SELECT timestamp FROM transactions WHERE id = ?",
                (target_tx_id,),
            )
            tx = await cursor.fetchone()
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
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [self._row_to_fact(row) for row in rows]

    async def time_travel(
        self,
        tx_id: int,
        project: str | None = None,
    ) -> list[Fact]:
        async with self.session() as conn:
            clause, params = time_travel_filter(tx_id, table_alias="f")
            query = f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} WHERE {clause}"
            if project:
                query += " AND f.project = ?"
                params.append(project)
            query += " ORDER BY f.id ASC"
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [self._row_to_fact(row) for row in rows]

    async def stats(self) -> dict:
        async with self.session() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM facts")
            total = (await cursor.fetchone())[0]

            cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE valid_until IS NULL")
            active = (await cursor.fetchone())[0]

            cursor = await conn.execute(
                "SELECT DISTINCT project FROM facts WHERE valid_until IS NULL"
            )
            projects = [p[0] for p in await cursor.fetchall()]

            cursor = await conn.execute(
                "SELECT fact_type, COUNT(*) FROM facts WHERE valid_until IS NULL GROUP BY fact_type"
            )
            types = dict(await cursor.fetchall())

            cursor = await conn.execute("SELECT COUNT(*) FROM transactions")
            tx_count = (await cursor.fetchone())[0]

            db_size = self._db_path.stat().st_size / (1024 * 1024) if self._db_path.exists() else 0

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
        """Get entity graph for a project."""
        from cortex.graph import get_graph

        async with self.session() as conn:
            return await get_graph(conn, project)

    async def query_entity(
        self,
        name: str,
        project: Optional[str] = None,
    ) -> list[dict]:
        """Query a specific entity by name."""
        from cortex.graph import query_entity

        async with self.session() as conn:
            return await query_entity(conn, name, project)

    async def find_path(
        self,
        source: str,
        target: str,
        max_depth: int = 3,
    ) -> list[dict]:
        """Find paths between two entities."""
        from cortex.graph import find_path

        async with self.session() as conn:
            return await find_path(conn, source, target, max_depth)

    async def get_context_subgraph(
        self,
        seeds: list[str],
        depth: int = 2,
        max_nodes: int = 50,
    ) -> dict:
        """Retrieve a subgraph context for RAG."""
        from cortex.graph import get_context_subgraph

        async with self.session() as conn:
            return await get_context_subgraph(conn, seeds, depth, max_nodes)

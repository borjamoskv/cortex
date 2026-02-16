"""Fact Sovereign Layer — FactManager for CORTEX."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional


from cortex.engine.models import Fact, row_to_fact
from cortex.search import SearchResult, semantic_search, text_search
from cortex.temporal import build_temporal_filter_params, now_iso

logger = logging.getLogger("cortex.facts")

_FACT_COLUMNS = (
    "f.id, f.project, f.content, f.fact_type, f.tags, f.confidence, "
    "f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score, "
    "f.created_at, f.updated_at, f.tx_id, t.hash"
)
_FACT_JOIN = "FROM facts f LEFT JOIN transactions t ON f.tx_id = t.id"


class FactManager:
    """Manages the full lifecycle and retrieval of facts."""

    def __init__(self, engine):
        self.engine = engine

    async def store(
        self,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: Optional[List[str]] = None,
        confidence: str = "stated",
        source: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        valid_from: Optional[str] = None,
        commit: bool = True,
        tx_id: Optional[int] = None,
    ) -> int:
        if not project or not project.strip():
            raise ValueError("project cannot be empty")
        if not content or not content.strip():
            raise ValueError("content cannot be empty")

        conn = await self.engine.get_conn()
        ts = valid_from or now_iso()
        tags_json = json.dumps(tags or [])
        meta_json = json.dumps(meta or {})

        cursor = await conn.execute(
            "INSERT INTO facts (project, content, fact_type, tags, confidence, "
            "valid_from, source, meta, created_at, updated_at, tx_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                project,
                content,
                fact_type,
                tags_json,
                confidence,
                ts,
                source,
                meta_json,
                ts,
                ts,
                tx_id,
            ),
        )
        fact_id = cursor.lastrowid

        # Embedding integration via engine's embedding component
        if self.engine._auto_embed and self.engine._vec_available:
            try:
                embedding = self.engine.embeddings.embed(content)
                await conn.execute(
                    "INSERT INTO fact_embeddings (fact_id, embedding) VALUES (?, ?)",
                    (fact_id, json.dumps(embedding)),
                )
            except Exception as e:
                logger.warning("Embedding failed for fact %d: %s", fact_id, e)

        from cortex.graph import process_fact_graph

        try:
            await process_fact_graph(conn, fact_id, content, project, ts)
        except Exception as e:
            logger.warning("Graph extraction failed for fact %d: %s", fact_id, e)

        tx_id = await self.engine._log_transaction(
            conn, project, "store", {"fact_id": fact_id, "fact_type": fact_type}
        )
        await conn.execute("UPDATE facts SET tx_id = ? WHERE id = ?", (tx_id, fact_id))

        if commit:
            await conn.commit()

        return fact_id

    async def search(
        self,
        query: str,
        project: Optional[str] = None,
        top_k: int = 5,
        as_of: Optional[str] = None,
        **kwargs,
    ) -> list[SearchResult]:
        if not query or not query.strip():
            raise ValueError("query cannot be empty")
        conn = await self.engine.get_conn()
        try:
            results = await semantic_search(
                conn, self.engine.embeddings.embed(query), top_k, project, as_of
            )
            if results:
                return results
        except Exception as e:
            logger.warning("Semantic search failed: %s", e)
        return await text_search(conn, query, project, limit=top_k, **kwargs)

    async def recall(
        self, project: str, limit: Optional[int] = None, offset: int = 0
    ) -> list[Fact]:
        conn = await self.engine.get_conn()
        query = f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} WHERE f.project = ? AND f.valid_until IS NULL ORDER BY (f.consensus_score * 0.8 + (1.0 / (1.0 + (julianday('now') - julianday(f.created_at)))) * 0.2) DESC, f.fact_type, f.created_at DESC"
        params: list = [project]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        if offset:
            query += " OFFSET ?"
            params.append(offset)
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [row_to_fact(row) for row in rows]

    async def update(
        self,
        fact_id: int,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> int:
        conn = await self.engine.get_conn()
        cursor = await conn.execute(
            "SELECT project, content, fact_type, tags, confidence, source, meta "
            "FROM facts WHERE id = ? AND valid_until IS NULL",
            (fact_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Fact {fact_id} not found")

        (project, old_content, fact_type, old_tags_json, confidence, source, old_meta_json) = row
        new_meta = json.loads(old_meta_json) if old_meta_json else {}
        if meta:
            new_meta.update(meta)
        new_meta["previous_fact_id"] = fact_id

        new_id = await self.store(
            project=project,
            content=content if content is not None else old_content,
            fact_type=fact_type,
            tags=tags if tags is not None else json.loads(old_tags_json),
            confidence=confidence,
            source=source,
            meta=new_meta,
        )
        await self.deprecate(fact_id, reason=f"updated_by_{new_id}")
        return new_id

    async def deprecate(self, fact_id: int, reason: Optional[str] = None) -> bool:
        conn = await self.engine.get_conn()
        ts = now_iso()
        cursor = await conn.execute(
            "UPDATE facts SET valid_until = ?, updated_at = ?, "
            "meta = json_set(COALESCE(meta, '{}'), '$.deprecation_reason', ?) "
            "WHERE id = ? AND valid_until IS NULL",
            (ts, ts, reason or "deprecated", fact_id),
        )

        if cursor.rowcount > 0:
            cursor = await conn.execute("SELECT project FROM facts WHERE id = ?", (fact_id,))
            row = await cursor.fetchone()
            await self.engine._log_transaction(
                conn,
                row[0] if row else "unknown",
                "deprecate",
                {"fact_id": fact_id, "reason": reason},
            )
            # CDC: Encole for Neo4j sync
            await conn.execute(
                "INSERT INTO graph_outbox (fact_id, action, status) VALUES (?, ?, ?)",
                (fact_id, "deprecate_fact", "pending"),
            )
            await conn.commit()
            return True
        return False

    async def history(self, project: str, as_of: Optional[str] = None) -> list[Fact]:
        conn = await self.engine.get_conn()
        if as_of:
            clause, params = build_temporal_filter_params(as_of, table_alias="f")
            query = f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} WHERE f.project = ? AND {clause} ORDER BY f.valid_from DESC"
            cursor = await conn.execute(query, [project] + params)
        else:
            query = f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} WHERE f.project = ? ORDER BY f.valid_from DESC"
            cursor = await conn.execute(query, (project,))
        rows = await cursor.fetchall()
        return [row_to_fact(row) for row in rows]

    async def register_ghost(self, reference: str, context: str, project: str) -> int:
        conn = await self.engine.get_conn()
        cursor = await conn.execute(
            "SELECT id FROM ghosts WHERE reference = ? AND project = ?", (reference, project)
        )
        row = await cursor.fetchone()
        if row:
            return row[0]

        ts = now_iso()
        cursor = await conn.execute(
            "INSERT INTO ghosts (reference, context, project, status, created_at) VALUES (?, ?, ?, 'open', ?)",
            (reference, context, project, ts),
        )
        ghost_id = cursor.lastrowid
        await conn.commit()
        return ghost_id

    async def stats(self) -> dict:
        conn = await self.engine.get_conn()
        cursor = await conn.execute("SELECT COUNT(*) FROM facts")
        total = (await cursor.fetchone())[0]

        cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE valid_until IS NULL")
        active = (await cursor.fetchone())[0]

        cursor = await conn.execute("SELECT DISTINCT project FROM facts WHERE valid_until IS NULL")
        projects = [p[0] for p in await cursor.fetchall()]

        cursor = await conn.execute(
            "SELECT fact_type, COUNT(*) FROM facts WHERE valid_until IS NULL GROUP BY fact_type"
        )
        types = dict(await cursor.fetchall())

        cursor = await conn.execute("SELECT COUNT(*) FROM transactions")
        tx_count = (await cursor.fetchone())[0]

        db_size = (
            self.engine._db_path.stat().st_size / (1024 * 1024)
            if self.engine._db_path.exists()
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
            "db_path": str(self.engine._db_path),
            "db_size_mb": round(db_size, 2),
        }

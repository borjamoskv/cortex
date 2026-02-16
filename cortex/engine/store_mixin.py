"""Storage mixin — store, update, deprecate, ghost management."""
from __future__ import annotations

import json
import logging
import aiosqlite
from typing import Any, Dict, List, Optional

from cortex.temporal import now_iso

logger = logging.getLogger("cortex")


class StoreMixin:
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

        conn = await self.get_conn()
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

        if self._auto_embed and self._vec_available:
            try:
                # LocalEmbedder might still be synchronous, usually fine if local
                embedding = self._get_embedder().embed(content)
                await conn.execute(
                    "INSERT INTO fact_embeddings (fact_id, embedding) "
                    "VALUES (?, ?)",
                    (fact_id, json.dumps(embedding)),
                )
            except Exception as e:
                logger.warning("Embedding failed for fact %d: %s", fact_id, e)

        from cortex.graph import process_fact_graph
        # Note: If graph extraction is high-CPU, we might still want threads, 
        # but for now we keep it sequential unless needed.
        # process_fact_graph needs to be async too ideally.
        try:
             # run_in_executor if it's slow, but let's assume async for now
             await process_fact_graph(conn, fact_id, content, project, ts)
        except Exception as e:
            logger.warning(
                "Graph extraction failed for fact %d: %s", fact_id, e
            )

        tx_id = await self._log_transaction(
            conn, project, "store", {"fact_id": fact_id, "fact_type": fact_type}
        )
        await conn.execute(
            "UPDATE facts SET tx_id = ? WHERE id = ?", (tx_id, fact_id)
        )

        if commit:
            await conn.commit()

        return fact_id

    async def store_many(self, facts: List[Dict[str, Any]]) -> List[int]:
        if not facts:
            raise ValueError("facts list cannot be empty")
        ids = []
        conn = await self.get_conn()
        try:
            for fact in facts:
                if "project" not in fact:
                    raise ValueError("project cannot be empty")
                if "content" not in fact:
                    raise ValueError("content cannot be empty")
                ids.append(await self.store(commit=False, **fact))
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
        return ids

    async def update(
        self,
        fact_id: int,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> int:
        conn = await self.get_conn()
        cursor = await conn.execute(
            "SELECT project, content, fact_type, tags, confidence, source, meta "
            "FROM facts WHERE id = ? AND valid_until IS NULL",
            (fact_id,),
        )
        row = await cursor.fetchone()

        if not row:
            raise ValueError(f"Fact {fact_id} not found")

        (
            project,
            old_content,
            fact_type,
            old_tags_json,
            confidence,
            source,
            old_meta_json,
        ) = row

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
        if not isinstance(fact_id, int) or fact_id <= 0:
            raise ValueError("Invalid fact_id")
        conn = await self.get_conn()
        ts = now_iso()
        cursor = await conn.execute(
            "UPDATE facts SET valid_until = ?, updated_at = ?, "
            "meta = json_set(COALESCE(meta, '{}'), '$.deprecation_reason', ?) "
            "WHERE id = ? AND valid_until IS NULL",
            (ts, ts, reason or "deprecated", fact_id),
        )

        if cursor.rowcount > 0:
            cursor = await conn.execute(
                "SELECT project FROM facts WHERE id = ?", (fact_id,)
            )
            row = await cursor.fetchone()
            await self._log_transaction(
                conn,
                row[0] if row else "unknown",
                "deprecate",
                {"fact_id": fact_id, "reason": reason},
            )
            # CDC: Encole for Neo4j sync
            await conn.execute(
                "INSERT INTO graph_outbox (fact_id, action, status) VALUES (?, ?, ?)",
                (fact_id, "deprecate_fact", "pending")
            )
            await conn.commit()
            return True
        return False

    async def register_ghost(
        self, reference: str, context: str, project: str
    ) -> int:
        conn = await self.get_conn()
        # Check if exists (idempotency)
        cursor = await conn.execute(
            "SELECT id FROM ghosts WHERE reference = ? AND project = ?",
            (reference, project),
        )
        row = await cursor.fetchone()
        if row:
            return row[0]

        ts = now_iso()
        cursor = await conn.execute(
            "INSERT INTO ghosts "
            "(reference, context, project, status, created_at) "
            "VALUES (?, ?, ?, 'open', ?)",
            (reference, context, project, ts),
        )
        ghost_id = cursor.lastrowid
        await conn.commit()
        return ghost_id

    async def resolve_ghost(
        self, ghost_id: int, target_entity_id: int, confidence: float = 1.0
    ) -> bool:
        conn = await self.get_conn()
        ts = now_iso()
        cursor = await conn.execute(
            "UPDATE ghosts SET status = 'resolved', target_id = ?, "
            "confidence = ?, resolved_at = ? WHERE id = ?",
            (target_entity_id, confidence, ts, ghost_id),
        )
        await conn.commit()
        return cursor.rowcount > 0

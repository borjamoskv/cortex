"""Storage mixin — store, update, deprecate, ghost management."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import aiosqlite

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
        conn: Optional[aiosqlite.Connection] = None,
    ) -> int:
        """Store a new fact with proper connection management."""
        if conn:
            return await self._store_impl(
                conn,
                project,
                content,
                fact_type,
                tags,
                confidence,
                source,
                meta,
                valid_from,
                commit,
                tx_id,
            )

        async with self.session() as conn:
            return await self._store_impl(
                conn,
                project,
                content,
                fact_type,
                tags,
                confidence,
                source,
                meta,
                valid_from,
                commit,
                tx_id,
            )

    async def _store_impl(
        self,
        conn: aiosqlite.Connection,
        project: str,
        content: str,
        fact_type: str,
        tags: Optional[List[str]],
        confidence: str,
        source: Optional[str],
        meta: Optional[Dict[str, Any]],
        valid_from: Optional[str],
        commit: bool,
        tx_id: Optional[int],
    ) -> int:
        if not project or not project.strip():
            raise ValueError("project cannot be empty")
        if not content or not content.strip():
            raise ValueError("content cannot be empty")

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

        if getattr(self, "_auto_embed", False) and getattr(self, "_vec_available", False):
            try:
                embedding = self._get_embedder().embed(content)
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

        new_tx_id = await self._log_transaction(
            conn, project, "store", {"fact_id": fact_id, "fact_type": fact_type}
        )
        await conn.execute("UPDATE facts SET tx_id = ? WHERE id = ?", (new_tx_id, fact_id))

        if commit:
            await conn.commit()

        return fact_id

    async def store_many(self, facts: List[Dict[str, Any]]) -> List[int]:
        if not facts:
            raise ValueError("facts list cannot be empty")

        async with self.session() as conn:
            ids = []
            try:
                for fact in facts:
                    if "project" not in fact:
                        raise ValueError("project cannot be empty")
                    if "content" not in fact:
                        raise ValueError("content cannot be empty")
                    ids.append(await self.store(commit=False, conn=conn, **fact))
                await conn.commit()
                return ids
            except Exception:
                await conn.rollback()
                raise

    async def update(
        self,
        fact_id: int,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> int:
        async with self.session() as conn:
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

            # Pass conn to store to maintain transaction
            new_id = await self.store(
                project=project,
                content=content if content is not None else old_content,
                fact_type=fact_type,
                tags=tags if tags is not None else json.loads(old_tags_json),
                confidence=confidence,
                source=source,
                meta=new_meta,
                conn=conn,
                commit=False,
            )
            await self.deprecate(fact_id, reason=f"updated_by_{new_id}", conn=conn)
            await conn.commit()
            return new_id

    async def deprecate(
        self,
        fact_id: int,
        reason: Optional[str] = None,
        conn: Optional[aiosqlite.Connection] = None,
    ) -> bool:
        if not isinstance(fact_id, int) or fact_id <= 0:
            raise ValueError("Invalid fact_id")

        if conn:
            return await self._deprecate_impl(conn, fact_id, reason)

        async with self.session() as conn:
            res = await self._deprecate_impl(conn, fact_id, reason)
            await conn.commit()
            return res

    async def _deprecate_impl(
        self, conn: aiosqlite.Connection, fact_id: int, reason: Optional[str]
    ) -> bool:
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
            await self._log_transaction(
                conn,
                row[0] if row else "unknown",
                "deprecate",
                {"fact_id": fact_id, "reason": reason},
            )
            # CDC: Enqueue for Neo4j sync
            await conn.execute(
                "INSERT INTO graph_outbox (fact_id, action, status) VALUES (?, ?, ?)",
                (fact_id, "deprecate_fact", "pending"),
            )
            return True
        return False

    async def register_ghost(
        self,
        reference: str,
        context: str,
        project: str,
        conn: Optional[aiosqlite.Connection] = None,
    ) -> int:
        if conn:
            return await self._register_ghost_impl(conn, reference, context, project)

        async with self.session() as conn:
            res = await self._register_ghost_impl(conn, reference, context, project)
            await conn.commit()
            return res

    async def _register_ghost_impl(
        self, conn: aiosqlite.Connection, reference: str, context: str, project: str
    ) -> int:
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
        return cursor.lastrowid

    async def resolve_ghost(
        self,
        ghost_id: int,
        target_entity_id: int,
        confidence: float = 1.0,
        conn: Optional[aiosqlite.Connection] = None,
    ) -> bool:
        if conn:
            return await self._resolve_ghost_impl(conn, ghost_id, target_entity_id, confidence)

        async with self.session() as conn:
            res = await self._resolve_ghost_impl(conn, ghost_id, target_entity_id, confidence)
            await conn.commit()
            return res

    async def _resolve_ghost_impl(
        self, conn: aiosqlite.Connection, ghost_id: int, target_entity_id: int, confidence: float
    ) -> bool:
        ts = now_iso()
        cursor = await conn.execute(
            "UPDATE ghosts SET status = 'resolved', target_id = ?, "
            "confidence = ?, resolved_at = ? WHERE id = ?",
            (target_entity_id, confidence, ts, ghost_id),
        )
        return cursor.rowcount > 0

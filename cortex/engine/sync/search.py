"""Sync Search module for CORTEX."""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger("cortex.engine.sync.search")


class SyncSearchMixin:
    def search_sync(
        self,
        query: str,
        project: str | None = None,
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
                embedding = self.embeddings._get_embedder().embed(query)
                results = semantic_search_sync(
                    conn,
                    embedding,
                    top_k=top_k,
                    project=project,
                )
                if results:
                    return results
            except (sqlite3.Error, OSError, RuntimeError) as e:
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

        embedding = self.embeddings._get_embedder().embed(query)
        return hybrid_search_sync(
            conn,
            query,
            embedding,
            top_k=top_k,
            project=project,
            vector_weight=vector_weight,
            text_weight=text_weight,
        )

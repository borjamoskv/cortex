"""Sync Graph module for CORTEX."""

from __future__ import annotations

import logging
from typing import Optional
from cortex.temporal import now_iso

logger = logging.getLogger("cortex.engine.sync.graph")


class SyncGraphMixin:
    def graph_sync(self, project: Optional[str] = None, limit: int = 50) -> dict:
        """Retrieve the graph synchronously."""
        from cortex.graph.backends.sqlite import SQLiteBackend

        conn = self._get_sync_conn()
        return SQLiteBackend(conn).get_graph_sync(project=project, limit=limit)

    def query_entity_sync(self, name: str, project: Optional[str] = None) -> Optional[dict]:
        """Query an entity and its connections synchronously."""
        from cortex.graph.backends.sqlite import SQLiteBackend

        conn = self._get_sync_conn()
        return SQLiteBackend(conn).query_entity_sync(name=name, project=project)

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

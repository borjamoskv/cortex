""" Query mixin — search, recall, history, reconstruct_state, stats. """
from __future__ import annotations
import json
import logging
import sqlite3
from typing import Optional
from cortex.engine.models import Fact
from cortex.search import SearchResult, semantic_search, text_search
from cortex.temporal import build_temporal_filter_params, now_iso

logger = logging.getLogger("cortex")

class QueryMixin:
    def search(self, query: str, project: Optional[str] = None, top_k: int = 5, as_of: Optional[str] = None, **kwargs) -> list[SearchResult]:
        if not query or not query.strip(): raise ValueError("query cannot be empty")
        conn = self._get_conn()
        try:
            results = semantic_search(conn, self._get_embedder().embed(query), top_k, project, as_of)
            if results: return results
        except Exception as e:
            logger.warning("Semantic search failed: %s", e)
        return text_search(conn, query, project, limit=top_k, **kwargs)

    def recall(self, project: str, limit: Optional[int] = None, offset: int = 0) -> list[Fact]:
        conn = self._get_conn()
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
        cursor = conn.execute(query, params)
        return [self._row_to_fact(row) for row in cursor.fetchall()]

    def history(self, project: str, as_of: Optional[str] = None) -> list[Fact]:
        conn = self._get_conn()
        if as_of:
            clause, params = build_temporal_filter_params(as_of, table_alias="f")
            query = f"SELECT f.id, f.project, f.content, f.fact_type, f.tags, f.confidence, f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score, f.created_at, f.updated_at, f.tx_id, t.hash FROM facts f LEFT JOIN transactions t ON f.tx_id = t.id WHERE f.project = ? AND {clause} ORDER BY f.valid_from DESC"
            cursor = conn.execute(query, [project] + params)
        else:
            cursor = conn.execute("SELECT f.id, f.project, f.content, f.fact_type, f.tags, f.confidence, f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score, f.created_at, f.updated_at, f.tx_id, t.hash FROM facts f LEFT JOIN transactions t ON f.tx_id = t.id WHERE f.project = ? ORDER BY f.valid_from DESC", (project,))
        return [self._row_to_fact(row) for row in cursor.fetchall()]

    def reconstruct_state(self, target_tx_id: int, project: Optional[str] = None) -> list[Fact]:
        conn = self._get_conn()
        tx = conn.execute("SELECT timestamp FROM transactions WHERE id = ?", (target_tx_id,)).fetchone()
        if not tx: raise ValueError(f"Transaction {target_tx_id} not found")
        tx_time = tx[0]
        query = "SELECT f.id, f.project, f.content, f.fact_type, f.tags, f.confidence, f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score, f.created_at, f.updated_at, f.tx_id, t.hash FROM facts f LEFT JOIN transactions t ON f.tx_id = t.id WHERE (f.created_at <= ? AND (f.valid_until IS NULL OR f.valid_until > ?)) AND (f.tx_id IS NULL OR f.tx_id <= ?)"
        params = [tx_time, tx_time, target_tx_id]
        if project: query += " AND f.project = ?"; params.append(project)
        query += " ORDER BY id ASC"
        cursor = conn.execute(query, params)
        return [self._row_to_fact(row) for row in cursor.fetchall()]

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM facts WHERE valid_until IS NULL").fetchone()[0]
        projects = [p[0] for p in conn.execute("SELECT DISTINCT project FROM facts WHERE valid_until IS NULL").fetchall()]
        types = {t: c for t, c in conn.execute("SELECT fact_type, COUNT(*) FROM facts WHERE valid_until IS NULL GROUP BY fact_type").fetchall()}
        tx_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        return {"total_facts": total, "active_facts": active, "deprecated_facts": total-active, "projects": projects, "project_count": len(projects), "types": types, "transactions": tx_count}

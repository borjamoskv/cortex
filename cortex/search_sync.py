"""
CORTEX v4.0 — Synchronous Search Engine.

Sync equivalents of search.py for use by CortexEngine.search_sync(),
cortex_bridge.py recall_context, and any sync caller.

Combines semantic vector search (sqlite-vec) with full-text search
for hybrid retrieval using Reciprocal Rank Fusion (RRF).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("cortex.search_sync")

# RRF smoothing constant (standard value from the RRF paper)
RRF_K = 60

# Shared SQL fragment
_PROJECT_FILTER = " AND f.project = ?"


@dataclass
class SyncSearchResult:
    """A single search result from sync search."""

    fact_id: int
    content: str
    project: str
    fact_type: str
    score: float = 0.0
    source: Optional[str] = None
    confidence: str = "stated"
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.fact_id,
            "content": self.content,
            "project": self.project,
            "type": self.fact_type,
            "score": round(self.score, 4),
            "source": self.source,
        }


def semantic_search_sync(
    conn: sqlite3.Connection,
    query_embedding: list[float],
    top_k: int = 5,
    project: Optional[str] = None,
) -> list[SyncSearchResult]:
    """Vector KNN search using sqlite-vec (sync)."""
    embedding_json = json.dumps(query_embedding)

    sql = """
        SELECT
            f.id, f.content, f.project, f.fact_type, f.confidence,
            f.source, f.tags, ve.distance
        FROM fact_embeddings AS ve
        JOIN facts AS f ON f.id = ve.fact_id
        WHERE ve.embedding MATCH ?
            AND k = ?
            AND f.valid_until IS NULL
    """
    params: list = [embedding_json, top_k * 3]

    if project:
        sql += _PROJECT_FILTER
        params.append(project)

    sql += " ORDER BY ve.distance ASC"

    try:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
    except (sqlite3.Error, ValueError) as e:
        logger.error("Semantic search sync failed: %s", e)
        return []

    results = []
    for row in rows[:top_k]:
        try:
            tags = json.loads(row[6]) if row[6] else []
        except (json.JSONDecodeError, TypeError):
            tags = []

        # Convert distance to similarity score (1 - distance for cosine)
        score = max(0.0, 1.0 - (row[7] if row[7] else 0.0))
        results.append(SyncSearchResult(
            fact_id=row[0],
            content=row[1],
            project=row[2],
            fact_type=row[3],
            confidence=row[4],
            source=row[5],
            tags=tags,
            score=score,
        ))

    return results


def _has_fts5_sync(conn: sqlite3.Connection) -> bool:
    """Check if facts_fts virtual table exists (sync)."""
    try:
        cursor = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='facts_fts'"
        )
        return cursor.fetchone() is not None
    except sqlite3.Error:
        return False


def _sanitize_fts_query(query: str) -> str:
    """Sanitize user input for FTS5 MATCH syntax."""
    tokens = query.split()
    safe_tokens = []
    for token in tokens:
        cleaned = token.replace('"', '').replace("'", "")
        if cleaned and cleaned.upper() not in ("AND", "OR", "NOT"):
            safe_tokens.append(f'"{cleaned}"')
    return " ".join(safe_tokens) if safe_tokens else f'"{query}"'


def _build_fts_query(
    query: str, project: Optional[str], limit: int,
) -> tuple[str, list]:
    """Build FTS5 MATCH query."""
    fts_query = _sanitize_fts_query(query)
    sql = """
        SELECT f.id, f.content, f.project, f.fact_type, f.confidence,
               f.source, f.tags, bm25(facts_fts) AS rank
        FROM facts_fts fts
        JOIN facts f ON f.id = fts.rowid
        WHERE fts.content MATCH ?
            AND f.valid_until IS NULL
    """
    params: list = [fts_query]
    if project:
        sql += _PROJECT_FILTER
        params.append(project)
    sql += " ORDER BY rank ASC LIMIT ?"
    params.append(limit)
    return sql, params


def _build_like_query(
    query: str, project: Optional[str], limit: int,
) -> tuple[str, list]:
    """Build LIKE fallback query."""
    sql = """
        SELECT f.id, f.content, f.project, f.fact_type, f.confidence,
               f.source, f.tags
        FROM facts f
        WHERE f.content LIKE ?
            AND f.valid_until IS NULL
    """
    params: list = [f"%{query}%"]
    if project:
        sql += _PROJECT_FILTER
        params.append(project)
    sql += " ORDER BY f.updated_at DESC LIMIT ?"
    params.append(limit)
    return sql, params


def _parse_row(row: tuple, has_rank: bool) -> SyncSearchResult:
    """Parse a database row into a SyncSearchResult."""
    try:
        tags = json.loads(row[6]) if row[6] else []
    except (json.JSONDecodeError, TypeError):
        tags = []

    if has_rank and len(row) > 7:
        score = -row[7] if row[7] else 0.5
    else:
        score = 0.5

    return SyncSearchResult(
        fact_id=row[0],
        content=row[1],
        project=row[2],
        fact_type=row[3],
        confidence=row[4],
        source=row[5],
        tags=tags,
        score=score,
    )


def text_search_sync(
    conn: sqlite3.Connection,
    query: str,
    project: Optional[str] = None,
    limit: int = 20,
) -> list[SyncSearchResult]:
    """Full-text search with FTS5 (fast) and LIKE fallback (sync)."""
    use_fts = _has_fts5_sync(conn)

    try:
        if use_fts:
            sql, params = _build_fts_query(query, project, limit)
        else:
            sql, params = _build_like_query(query, project, limit)

        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
    except (sqlite3.Error, ValueError) as e:
        logger.error("Text search sync failed: %s", e)
        return []

    return [_parse_row(row, use_fts) for row in rows]


def hybrid_search_sync(
    conn: sqlite3.Connection,
    query: str,
    query_embedding: list[float],
    top_k: int = 10,
    project: Optional[str] = None,
    vector_weight: float = 0.6,
    text_weight: float = 0.4,
) -> list[SyncSearchResult]:
    """Hybrid search combining semantic + text via Reciprocal Rank Fusion (sync).

    RRF merges ranked lists without requiring score normalization:
        score(d) = Σ weight_i / (k + rank_i(d))
    """
    sem_results = semantic_search_sync(
        conn, query_embedding, top_k=top_k * 2, project=project,
    )
    txt_results = text_search_sync(
        conn, query, project=project, limit=top_k * 2,
    )

    # Build RRF scores by fact_id
    rrf_scores: dict[int, float] = {}
    result_map: dict[int, SyncSearchResult] = {}

    for rank, result in enumerate(sem_results):
        rrf_scores[result.fact_id] = (
            rrf_scores.get(result.fact_id, 0.0)
            + vector_weight / (RRF_K + rank + 1)
        )
        result_map[result.fact_id] = result

    for rank, result in enumerate(txt_results):
        rrf_scores[result.fact_id] = (
            rrf_scores.get(result.fact_id, 0.0)
            + text_weight / (RRF_K + rank + 1)
        )
        if result.fact_id not in result_map:
            result_map[result.fact_id] = result

    # Sort by RRF score descending
    sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:top_k]

    merged = []
    for fact_id in sorted_ids:
        result = result_map[fact_id]
        result.score = rrf_scores[fact_id]
        merged.append(result)

    logger.debug(
        "Hybrid search sync: %d semantic + %d text → %d merged (RRF)",
        len(sem_results), len(txt_results), len(merged),
    )
    return merged

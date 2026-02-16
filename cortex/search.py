"""
CORTEX v4.0 — Search Engine.

Combines semantic vector search (sqlite-vec) with full-text search
for hybrid retrieval using Reciprocal Rank Fusion (RRF).
Returns ranked results with normalized scores.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import aiosqlite
from dataclasses import dataclass, field
from typing import Optional
from cortex.temporal import build_temporal_filter_params

logger = logging.getLogger("cortex.search")

# ─── SQL fragment constants (DRY) ────────────────────────────────
_AND = " AND "
_FILTER_PROJECT = " AND f.project = ?"
_FILTER_ACTIVE = " AND f.valid_until IS NULL"


@dataclass
class SearchResult:
    """A single search result with metadata."""

    fact_id: int
    content: str
    project: str
    fact_type: str
    confidence: str
    valid_from: str
    valid_until: Optional[str]
    tags: list[str]
    created_at: str
    updated_at: str
    score: float = 0.0
    source: Optional[str] = None
    meta: dict = field(default_factory=dict)
    tx_id: Optional[int] = None
    hash: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.fact_id,
            "content": self.content,
            "project": self.project,
            "type": self.fact_type,
            "confidence": self.confidence,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "tags": self.tags,
            "score": round(self.score, 4),
            "source": self.source,
        }


async def semantic_search(
    conn: aiosqlite.Connection,
    query_embedding: list[float],
    top_k: int = 5,
    project: Optional[str] = None,
    as_of: Optional[str] = None,
) -> list[SearchResult]:
    """Perform semantic vector search using sqlite-vec."""
    # sqlite-vec KNN query
    embedding_json = json.dumps(query_embedding)

    sql = f"""
        SELECT
            f.id, f.content, f.project, f.fact_type, f.confidence,
            f.valid_from, f.valid_until, f.tags, f.source, f.meta,
            ve.distance, f.created_at, f.updated_at, f.tx_id, t.hash
        FROM fact_embeddings AS ve
        JOIN facts AS f ON f.id = ve.fact_id
        LEFT JOIN transactions t ON f.tx_id = t.id
        WHERE ve.embedding MATCH ?
            AND k = ?
    """

    params: list = [embedding_json, top_k * 3]  # Over-fetch for filtering

    if project:
        sql += _FILTER_PROJECT
        params.append(project)

    if as_of:
        clause, t_params = build_temporal_filter_params(as_of, table_alias="f")
        sql += _AND + clause
        params.extend(t_params)
    else:
        # Default to active facts
        sql += _FILTER_ACTIVE

    sql += " ORDER BY ve.distance ASC"

    try:
        cursor = await conn.execute(sql, params)
        rows = await cursor.fetchall()
    except (aiosqlite.Error, sqlite3.Error, ValueError) as e:
        logger.error("Semantic search failed: %s", e)
        return []

    results = []
    for row in rows[:top_k]:
        try:
            tags = json.loads(row[7]) if row[7] else []
        except (json.JSONDecodeError, TypeError):
            tags = []
            
        try:
            meta = json.loads(row[9]) if row[9] else {}
        except (json.JSONDecodeError, TypeError):
            meta = {}
        # Convert distance to similarity score (1 - distance for cosine)
        score = 1.0 - (row[10] if row[10] else 0.0)

        results.append(SearchResult(
            fact_id=row[0],
            content=row[1],
            project=row[2],
            fact_type=row[3],
            confidence=row[4],
            valid_from=row[5],
            valid_until=row[6],
            tags=tags,
            source=row[8],
            meta=meta,
            score=score,
            created_at=row[11] if len(row) > 11 else "unknown",
            updated_at=row[12] if len(row) > 12 else "unknown",
            tx_id=row[13] if len(row) > 13 else None,
            hash=row[14] if len(row) > 14 else None,
        ))

    return results


async def _has_fts5(conn: aiosqlite.Connection) -> bool:
    """Check if facts_fts virtual table exists."""
    try:
        cursor = await conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='facts_fts'"
        )
        return (await cursor.fetchone()) is not None
    except (aiosqlite.Error, sqlite3.Error):
        return False


def _sanitize_fts_query(query: str) -> str:
    """Sanitize user input for FTS5 MATCH syntax.

    FTS5 treats certain characters as operators (AND, OR, NOT, *, ", etc.).
    We escape double quotes and wrap each token in double quotes to force
    literal matching, then join with implicit AND.
    """
    # Remove FTS5 special chars that could cause syntax errors
    tokens = query.split()
    safe_tokens = []
    for token in tokens:
        # Strip FTS5 operators; keep alphanumeric + accented chars
        cleaned = token.replace('"', '').replace("'", "")
        if cleaned and cleaned.upper() not in ("AND", "OR", "NOT"):
            safe_tokens.append(f'"{cleaned}"')
    return " ".join(safe_tokens) if safe_tokens else f'"{query}"'


async def text_search(
    conn: aiosqlite.Connection,
    query: str,
    project: Optional[str] = None,
    fact_type: Optional[str] = None,
    tags: Optional[list[str]] = None,
    limit: int = 20,
    as_of: Optional[str] = None,
) -> list[SearchResult]:
    """Perform text search using FTS5 (fast) with LIKE fallback.

    If the facts_fts virtual table exists (migration 005), uses FTS5 MATCH
    with BM25 ranking. Otherwise falls back to LIKE %query% scan.
    """
    use_fts = await _has_fts5(conn)

    try:
        if use_fts:
            rows = await _fts5_search(conn, query, project, fact_type, tags, limit, as_of)
        else:
            rows = await _like_search(conn, query, project, fact_type, tags, limit, as_of)
    except (aiosqlite.Error, sqlite3.Error, ValueError, RuntimeError) as e:
        logger.error("Text search failed (%s): %s", type(e).__name__, e)
        return []

    return _rows_to_results(rows, is_fts=use_fts)


async def _fts5_search(
    conn: aiosqlite.Connection,
    query: str,
    project: Optional[str],
    fact_type: Optional[str],
    tags: Optional[list[str]],
    limit: int,
    as_of: Optional[str],
) -> list:
    """FTS5 MATCH search with BM25 ranking."""
    fts_query = _sanitize_fts_query(query)

    sql = """
        SELECT f.id, f.content, f.project, f.fact_type, f.confidence,
               f.valid_from, f.valid_until, f.tags, f.source, f.meta,
               f.created_at, f.updated_at, f.tx_id, t.hash,
               bm25(facts_fts) AS rank
        FROM facts_fts fts
        JOIN facts f ON f.id = fts.rowid
        LEFT JOIN transactions t ON f.tx_id = t.id
        WHERE fts.content MATCH ?
    """
    params: list = [fts_query]

    if as_of:
        clause, t_params = build_temporal_filter_params(as_of, table_alias="f")
        sql += " AND " + clause
        params.extend(t_params)
    else:
        sql += " AND f.valid_until IS NULL"

    if project:
        sql += " AND f.project = ?"
        params.append(project)

    if fact_type:
        sql += " AND f.fact_type = ?"
        params.append(fact_type)

    if tags:
        for tag in tags:
            sql += " AND f.tags LIKE ?"
            params.append(f'%"{tag}"%')

    # BM25 returns negative scores (lower = better match)
    sql += " ORDER BY rank ASC LIMIT ?"
    params.append(limit)

    cursor = await conn.execute(sql, params)
    return await cursor.fetchall()


async def _like_search(
    conn: aiosqlite.Connection,
    query: str,
    project: Optional[str],
    fact_type: Optional[str],
    tags: Optional[list[str]],
    limit: int,
    as_of: Optional[str],
) -> list:
    """Fallback LIKE %query% search."""
    sql = """
        SELECT f.id, f.content, f.project, f.fact_type, f.confidence,
               f.valid_from, f.valid_until, f.tags, f.source, f.meta,
               f.created_at, f.updated_at, f.tx_id, t.hash
        FROM facts f
        LEFT JOIN transactions t ON f.tx_id = t.id
        WHERE f.content LIKE ?
    """
    params: list = [f"%{query}%"]

    if as_of:
        clause, t_params = build_temporal_filter_params(as_of, table_alias="f")
        sql += " AND " + clause
        params.extend(t_params)
    else:
        sql += " AND f.valid_until IS NULL"

    if project:
        sql += " AND f.project = ?"
        params.append(project)

    if fact_type:
        sql += " AND f.fact_type = ?"
        params.append(fact_type)

    if tags:
        for tag in tags:
            sql += " AND f.tags LIKE ?"
            params.append(f'%"{tag}"%')

    sql += " ORDER BY f.updated_at DESC LIMIT ?"
    params.append(limit)

    cursor = await conn.execute(sql, params)
    return await cursor.fetchall()


def _rows_to_results(rows: list, is_fts: bool = False) -> list[SearchResult]:
    """Convert raw DB rows to SearchResult objects."""
    results = []
    for row in rows:
        try:
            row_tags = json.loads(row[7]) if row[7] else []
        except (json.JSONDecodeError, TypeError):
            row_tags = []

        try:
            meta = json.loads(row[9]) if row[9] else {}
        except (json.JSONDecodeError, TypeError):
            meta = {}

        if is_fts and len(row) > 14:
            # BM25 score: negate so higher = better (BM25 returns negative)
            score = -row[14] if row[14] else 0.5
        else:
            score = 0.5  # Flat score for LIKE fallback

        results.append(SearchResult(
            fact_id=row[0],
            content=row[1],
            project=row[2],
            fact_type=row[3],
            confidence=row[4],
            valid_from=row[5],
            valid_until=row[6],
            tags=row_tags,
            source=row[8],
            meta=meta,
            score=score,
            created_at=row[10] if len(row) > 10 else "unknown",
            updated_at=row[11] if len(row) > 11 else "unknown",
            tx_id=row[12] if len(row) > 12 else None,
            hash=row[13] if len(row) > 13 else None,
        ))

    return results


# ─── Reciprocal Rank Fusion (RRF) ────────────────────────────────────

RRF_K = 60  # Smoothing constant (standard value from the RRF paper)


async def hybrid_search(
    conn: aiosqlite.Connection,
    query: str,
    query_embedding: list[float],
    top_k: int = 10,
    project: Optional[str] = None,
    as_of: Optional[str] = None,
    vector_weight: float = 0.6,
    text_weight: float = 0.4,
) -> list[SearchResult]:
    """Hybrid search combining semantic + text via Reciprocal Rank Fusion.

    RRF merges ranked lists without requiring score normalization:
        score(d) = Σ weight_i / (k + rank_i(d))

    Args:
        vector_weight: Weight for semantic search results (default 0.6).
        text_weight: Weight for text search results (default 0.4).
    """
    # Run both searches (over-fetch for better fusion)
    sem_results = await semantic_search(
        conn, query_embedding, top_k=top_k * 2, project=project, as_of=as_of
    )
    txt_results = await text_search(
        conn, query, project=project, limit=top_k * 2, as_of=as_of
    )

    # Build RRF scores by fact_id
    rrf_scores: dict[int, float] = {}
    result_map: dict[int, SearchResult] = {}

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

    # Sort by RRF score descending, assign normalized scores
    sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:top_k]

    merged = []
    for fact_id in sorted_ids:
        result = result_map[fact_id]
        result.score = rrf_scores[fact_id]
        merged.append(result)

    logger.debug(
        "Hybrid search: %d semantic + %d text → %d merged (RRF)",
        len(sem_results), len(txt_results), len(merged),
    )
    return merged

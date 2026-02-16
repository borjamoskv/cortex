"""
CORTEX v4.0 — Search Engine.

Combines semantic vector search (sqlite-vec) with full-text search
for hybrid retrieval. Returns ranked results with scores.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from typing import Optional
from cortex.temporal import build_temporal_filter_params

logger = logging.getLogger("cortex.search")


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


def semantic_search(
    conn: sqlite3.Connection,
    query_embedding: list[float],
    top_k: int = 5,
    project: Optional[str] = None,
    as_of: Optional[str] = None,
) -> list[SearchResult]:
    """Perform semantic vector search using sqlite-vec.

    Args:
        conn: SQLite connection with vec0 loaded.
        query_embedding: 384-dim query vector.
        top_k: Number of results to return.
        project: Optional project scope filter.
        temporal_filter: Optional temporal SQL clause.

    Returns:
        List of SearchResult ordered by similarity.
    """
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
        sql += " AND f.project = ?"
        params.append(project)

    if as_of:
        clause, t_params = build_temporal_filter_params(as_of, table_alias="f")
        sql += " AND " + clause
        params.extend(t_params)
    else:
        # Default to active facts
        sql += " AND f.valid_until IS NULL"

    sql += " ORDER BY ve.distance ASC"

    try:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
    except (sqlite3.Error, ValueError) as e:
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


def text_search(
    conn: sqlite3.Connection,
    query: str,
    project: Optional[str] = None,
    fact_type: Optional[str] = None,
    tags: Optional[list[str]] = None,
    limit: int = 20,
    as_of: Optional[str] = None,
) -> list[SearchResult]:
    """Perform text search using LIKE (fallback when vectors unavailable).

    Args:
        conn: SQLite connection.
        query: Text to search for.
        project: Optional project scope filter.
        fact_type: Optional fact type filter.
        tags: Optional list of tags to require.
        limit: Maximum results.

    Returns:
        List of SearchResult ordered by relevance.
    """
    try:
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

        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
    except (sqlite3.Error, ValueError, RuntimeError):
        return []

    results = []
    for row in rows:
        try:
            tags = json.loads(row[7]) if row[7] else []
        except (json.JSONDecodeError, TypeError):
            tags = []
            
        try:
            meta = json.loads(row[9]) if row[9] else {}
        except (json.JSONDecodeError, TypeError):
            meta = {}

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
            score=0.5,  # Flat score for text search
            created_at=row[10] if len(row) > 10 else "unknown",
            updated_at=row[11] if len(row) > 11 else "unknown",
            tx_id=row[12] if len(row) > 12 else None,
            hash=row[13] if len(row) > 13 else None,
        ))

    return results

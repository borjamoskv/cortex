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
    score: float = 0.0
    source: Optional[str] = None
    meta: dict = field(default_factory=dict)

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
    temporal_filter: Optional[str] = None,
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
            ve.distance
        FROM fact_embeddings AS ve
        JOIN facts AS f ON f.id = ve.fact_id
        WHERE ve.embedding MATCH ?
            AND k = ?
    """

    params: list = [embedding_json, top_k * 3]  # Over-fetch for filtering

    if project:
        sql += " AND f.project = ?"
        params.append(project)

    if temporal_filter:
        sql += f" AND f.{temporal_filter}"

    sql += " ORDER BY ve.distance ASC"

    try:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        return []

    results = []
    for row in rows[:top_k]:
        tags = json.loads(row[7]) if row[7] else []
        meta = json.loads(row[9]) if row[9] else {}
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
        ))

    return results


def text_search(
    conn: sqlite3.Connection,
    query: str,
    project: Optional[str] = None,
    fact_type: Optional[str] = None,
    limit: int = 20,
) -> list[SearchResult]:
    """Perform text search using LIKE (fallback when vectors unavailable).

    Args:
        conn: SQLite connection.
        query: Text to search for.
        project: Optional project scope filter.
        fact_type: Optional fact type filter.
        limit: Maximum results.

    Returns:
        List of SearchResult ordered by relevance.
    """
    sql = """
        SELECT id, content, project, fact_type, confidence,
               valid_from, valid_until, tags, source, meta
        FROM facts
        WHERE content LIKE ?
          AND valid_until IS NULL
    """
    params: list = [f"%{query}%"]

    if project:
        sql += " AND project = ?"
        params.append(project)

    if fact_type:
        sql += " AND fact_type = ?"
        params.append(fact_type)

    sql += f" ORDER BY updated_at DESC LIMIT {limit}"

    cursor = conn.execute(sql, params)
    rows = cursor.fetchall()

    results = []
    for row in rows:
        tags = json.loads(row[7]) if row[7] else []
        meta = json.loads(row[9]) if row[9] else {}

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
        ))

    return results

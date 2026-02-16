# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Vector search implementation."""

import json
import logging
import sqlite3
from typing import Optional

import aiosqlite

from cortex.search.models import SearchResult
from cortex.temporal import build_temporal_filter_params

logger = logging.getLogger("cortex.search.vector")

# ─── SQL fragment constants ────────────────────────────────
_FILTER_PROJECT = " AND f.project = ?"
_FILTER_ACTIVE = " AND f.valid_until IS NULL"


async def semantic_search(
    conn: aiosqlite.Connection,
    query_embedding: list[float],
    top_k: int = 5,
    project: Optional[str] = None,
    as_of: Optional[str] = None,
) -> list[SearchResult]:
    """Perform semantic vector search using sqlite-vec."""
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

    params: list = [embedding_json, top_k * 3]

    if project:
        sql += _FILTER_PROJECT
        params.append(project)

    if as_of:
        clause, t_params = build_temporal_filter_params(as_of, table_alias="f")
        sql += " AND " + clause
        params.extend(t_params)
    else:
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
            meta = json.loads(row[9]) if row[9] else {}
        except (json.JSONDecodeError, TypeError):
            tags, meta = [], {}

        score = 1.0 - (row[10] if row[10] else 0.0)

        results.append(
            SearchResult(
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
                created_at=row[11],
                updated_at=row[12],
                tx_id=row[13],
                hash=row[14],
            )
        )
    return results


def semantic_search_sync(
    conn: sqlite3.Connection,
    query_embedding: list[float],
    top_k: int = 5,
    project: Optional[str] = None,
) -> list[SearchResult]:
    """Vector KNN search (sync)."""
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
        sql += _FILTER_PROJECT
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
        score = 1.0 - (row[7] if row[7] else 0.0)
        results.append(
            SearchResult(
                fact_id=row[0],
                content=row[1],
                project=row[2],
                fact_type=row[3],
                confidence=row[4],
                source=row[5],
                tags=tags,
                score=score,
                valid_from="unknown",
                valid_until=None,
                created_at="unknown",
                updated_at="unknown",
            )
        )
    return results

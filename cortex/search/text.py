# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Full-text search implementation."""

import logging
import sqlite3

import aiosqlite

from cortex.search.models import SearchResult
from cortex.search.utils import (
    _has_fts5,
    _has_fts5_sync,
    _parse_row_sync,
    _rows_to_results,
    _sanitize_fts_query,
)
from cortex.temporal import build_temporal_filter_params

logger = logging.getLogger("cortex.search.text")


async def text_search(
    conn: aiosqlite.Connection,
    query: str,
    project: str | None = None,
    fact_type: str | None = None,
    tags: list[str] | None = None,
    limit: int = 20,
    as_of: str | None = None,
) -> list[SearchResult]:
    """Perform text search (async)."""
    use_fts = await _has_fts5(conn)
    try:
        if use_fts:
            rows = await _fts5_search(conn, query, project, fact_type, tags, limit, as_of)
        else:
            rows = await _like_search(conn, query, project, fact_type, tags, limit, as_of)
    except (sqlite3.Error, OSError, ValueError) as e:
        logger.error("Text search failed: %s", e)
        return []
    return _rows_to_results(rows, is_fts=use_fts)


async def _fts5_search(conn, query, project, fact_type, tags, limit, as_of):
    fts_query = _sanitize_fts_query(query)
    sql = """
        SELECT f.id, f.content, f.project, f.fact_type, f.confidence,
               f.valid_from, f.valid_until, f.tags, f.source, f.meta,
               f.created_at, f.updated_at, f.tx_id, t.hash,
               bm25(facts_fts) AS rank
        FROM facts_fts fts JOIN facts f ON f.id = fts.rowid
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
            sql += " AND json_extract(f.tags, '$') LIKE ?"
            params.append(f"%{tag}%")
    sql += " ORDER BY rank ASC LIMIT ?"
    params.append(limit)
    cursor = await conn.execute(sql, params)
    return await cursor.fetchall()


async def _like_search(conn, query, project, fact_type, tags, limit, as_of):
    sql = """
        SELECT f.id, f.content, f.project, f.fact_type, f.confidence,
               f.valid_from, f.valid_until, f.tags, f.source, f.meta,
               f.created_at, f.updated_at, f.tx_id, t.hash
        FROM facts f LEFT JOIN transactions t ON f.tx_id = t.id
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
            sql += " AND json_extract(f.tags, '$') LIKE ?"
            params.append(f"%{tag}%")
    sql += " ORDER BY f.updated_at DESC LIMIT ?"
    params.append(limit)
    cursor = await conn.execute(sql, params)
    return await cursor.fetchall()


def text_search_sync(
    conn: sqlite3.Connection,
    query: str,
    project: str | None = None,
    limit: int = 20,
) -> list[SearchResult]:
    """Full-text search (sync)."""
    use_fts = _has_fts5_sync(conn)
    try:
        if use_fts:
            fts_query = _sanitize_fts_query(query)
            sql = """
                SELECT f.id, f.content, f.project, f.fact_type, f.confidence,
                       f.source, f.tags, bm25(facts_fts) AS rank
                FROM facts_fts fts JOIN facts f ON f.id = fts.rowid
                WHERE fts.content MATCH ? AND f.valid_until IS NULL
            """
            params: list = [fts_query]
            if project:
                sql += " AND f.project = ?"
                params.append(project)
            sql += " ORDER BY rank ASC LIMIT ?"
            params.append(limit)
        else:
            sql = "SELECT id, content, project, fact_type, confidence, source, tags FROM facts WHERE content LIKE ? AND valid_until IS NULL"
            params = [f"%{query}%"]
            if project:
                sql += " AND project = ?"
                params.append(project)
            sql += " LIMIT ?"
            params.append(limit)

        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
    except (sqlite3.Error, OSError, ValueError) as e:
        logger.error("Text search sync failed: %s", e)
        return []
    return [_parse_row_sync(row, use_fts) for row in rows]

# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Search utilities."""

import json
import sqlite3

import aiosqlite

from cortex.search.models import SearchResult


async def _has_fts5(conn: aiosqlite.Connection) -> bool:
    """Check if facts_fts virtual table exists."""
    try:
        cursor = await conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='facts_fts'"
        )
        return (await cursor.fetchone()) is not None
    except (aiosqlite.Error, sqlite3.Error):
        return False


def _has_fts5_sync(conn: sqlite3.Connection) -> bool:
    """Check if facts_fts virtual table exists (sync)."""
    try:
        cursor = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='facts_fts'")
        return cursor.fetchone() is not None
    except sqlite3.Error:
        return False


def _sanitize_fts_query(query: str) -> str:
    """Sanitize user input for FTS5 MATCH syntax."""
    tokens = query.split()
    safe_tokens = []
    for token in tokens:
        cleaned = token.replace('"', "").replace("'", "")
        if cleaned and cleaned.upper() not in ("AND", "OR", "NOT"):
            safe_tokens.append(f'"{cleaned}"')
    return " ".join(safe_tokens) if safe_tokens else f'"{query}"'


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
            score = -row[14] if row[14] else 0.5
        else:
            score = 0.5

        results.append(
            SearchResult(
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
            )
        )

    return results


def _parse_row_sync(row: tuple, has_rank: bool) -> SearchResult:
    """Parse a database row into a SearchResult (sync)."""
    try:
        tags = json.loads(row[6]) if row[6] else []
    except (json.JSONDecodeError, TypeError):
        tags = []

    if has_rank and len(row) > 7:
        score = -row[7] if row[7] else 0.5
    else:
        score = 0.5

    return SearchResult(
        fact_id=row[0],
        content=row[1],
        project=row[2],
        fact_type=row[3],
        confidence=row[4],
        source=row[5],
        tags=tags,
        score=score,
        valid_from="unknown",  # Sync rows often have fewer columns
        valid_until=None,
        created_at="unknown",
        updated_at="unknown",
    )

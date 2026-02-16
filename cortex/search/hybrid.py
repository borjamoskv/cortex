# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Hybrid search with RRF."""

import logging
import sqlite3
from typing import Optional

import aiosqlite

from cortex.search.models import SearchResult
from cortex.search.text import text_search, text_search_sync
from cortex.search.vector import semantic_search, semantic_search_sync

logger = logging.getLogger("cortex.search.hybrid")

RRF_K = 60


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
    """Hybrid search combining semantic + text via RRF (async)."""
    sem_results = await semantic_search(conn, query_embedding, top_k * 2, project, as_of)
    txt_results = await text_search(conn, query, project, limit=top_k * 2, as_of=as_of)

    rrf_scores: dict[int, float] = {}
    result_map: dict[int, SearchResult] = {}

    for rank, res in enumerate(sem_results):
        rrf_scores[res.fact_id] = rrf_scores.get(res.fact_id, 0.0) + vector_weight / (
            RRF_K + rank + 1
        )
        result_map[res.fact_id] = res

    for rank, res in enumerate(txt_results):
        rrf_scores[res.fact_id] = rrf_scores.get(res.fact_id, 0.0) + text_weight / (
            RRF_K + rank + 1
        )
        if res.fact_id not in result_map:
            result_map[res.fact_id] = res

    sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:top_k]
    merged = []
    for fid in sorted_ids:
        r = result_map[fid]
        r.score = rrf_scores[fid]
        merged.append(r)
    return merged


def hybrid_search_sync(
    conn: sqlite3.Connection,
    query: str,
    query_embedding: list[float],
    top_k: int = 10,
    project: Optional[str] = None,
    vector_weight: float = 0.6,
    text_weight: float = 0.4,
) -> list[SearchResult]:
    """Hybrid search combining semantic + text via RRF (sync)."""
    sem_results = semantic_search_sync(conn, query_embedding, top_k * 2, project)
    txt_results = text_search_sync(conn, query, project, limit=top_k * 2)

    rrf_scores: dict[int, float] = {}
    result_map: dict[int, SearchResult] = {}

    for rank, res in enumerate(sem_results):
        rrf_scores[res.fact_id] = rrf_scores.get(res.fact_id, 0.0) + vector_weight / (
            RRF_K + rank + 1
        )
        result_map[res.fact_id] = res

    for rank, res in enumerate(txt_results):
        rrf_scores[res.fact_id] = rrf_scores.get(res.fact_id, 0.0) + text_weight / (
            RRF_K + rank + 1
        )
        if res.fact_id not in result_map:
            result_map[res.fact_id] = res

    sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:top_k]
    merged = []
    for fid in sorted_ids:
        r = result_map[fid]
        r.score = rrf_scores[fid]
        merged.append(r)
    return merged

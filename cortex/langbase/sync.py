# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v4.2 — Langbase Sync.

Bidirectional synchronization between CORTEX facts and Langbase Memory.
- CORTEX → Langbase: export facts as documents for cloud RAG
- Langbase → CORTEX: import search results as enrichment facts
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.engine_async import AsyncCortexEngine
    from cortex.langbase.client import LangbaseClient

logger = logging.getLogger("cortex.langbase.sync")


def _fact_to_markdown(fact: dict) -> str:
    """Convert a CORTEX fact to a markdown document for Langbase Memory.

    Format:
        ---
        fact_id: 42
        project: cortex
        type: decision
        confidence: verified
        tags: architecture, design
        created: 2026-02-19T10:00:00Z
        ---

        [fact content here]
    """
    lines = ["---"]
    lines.append(f"fact_id: {fact.get('id', 'unknown')}")
    lines.append(f"project: {fact.get('project', 'unknown')}")
    lines.append(f"type: {fact.get('fact_type', 'knowledge')}")
    lines.append(f"confidence: {fact.get('confidence', 'unknown')}")

    tags = fact.get("tags")
    if tags:
        if isinstance(tags, list):
            lines.append(f"tags: {', '.join(tags)}")
        else:
            lines.append(f"tags: {tags}")

    created = fact.get("created_at", "")
    if created:
        lines.append(f"created: {created}")

    lines.append("---")
    lines.append("")
    lines.append(fact.get("content", ""))

    return "\n".join(lines)


async def sync_to_langbase(
    client: LangbaseClient,
    engine: AsyncCortexEngine,
    project: str,
    memory_name: str | None = None,
    *,
    limit: int = 500,
) -> dict:
    """Export CORTEX facts to Langbase Memory.

    Creates a Memory set named 'cortex-{project}' (or custom name)
    and uploads each fact as a markdown document.

    Args:
        client: Langbase API client
        engine: CORTEX async engine
        project: CORTEX project to export
        memory_name: Override memory name (default: cortex-{project})
        limit: Max facts to export

    Returns:
        Summary with counts and any errors
    """
    mem_name = memory_name or f"cortex-{project}"

    # 1. Ensure memory exists
    try:
        await client.create_memory(
            name=mem_name,
            description=f"CORTEX facts from project '{project}' — auto-synced",
        )
        logger.info("Created Langbase memory: %s", mem_name)
    except (ConnectionError, OSError, RuntimeError) as e:
        # Memory might already exist — that's fine
        if "already exists" not in str(e).lower() and "409" not in str(e):
            logger.warning("Memory creation note: %s", e)

    # 2. Recall facts from CORTEX
    facts = await engine.recall(project=project, limit=limit)
    if not facts:
        return {"synced": 0, "errors": 0, "memory": mem_name, "message": "No facts to sync"}

    # 3. Upload each fact as a document
    synced = 0
    errors = 0
    error_details: list[str] = []

    for fact in facts:
        fact_dict = {
            "id": fact.id,
            "project": fact.project,
            "content": fact.content,
            "fact_type": fact.fact_type,
            "confidence": fact.confidence,
            "tags": fact.tags,
            "created_at": str(fact.created_at) if fact.created_at else "",
        }

        doc_content = _fact_to_markdown(fact_dict)
        filename = f"fact-{fact.id}.md"

        try:
            await client.upload_document(
                memory_name=mem_name,
                content=doc_content,
                filename=filename,
                meta={"fact_id": fact.id, "project": project, "type": fact.fact_type},
            )
            synced += 1
        except (ConnectionError, OSError, RuntimeError) as e:
            errors += 1
            detail = f"Fact #{fact.id}: {e}"
            error_details.append(detail)
            logger.error("Failed to sync fact: %s", detail)

    result = {
        "synced": synced,
        "errors": errors,
        "total": len(facts),
        "memory": mem_name,
    }
    if error_details:
        result["error_details"] = error_details[:10]  # Cap for response size

    logger.info(
        "Sync to Langbase complete: %d/%d facts → memory '%s'",
        synced, len(facts), mem_name,
    )
    return result


async def enrich_from_langbase(
    client: LangbaseClient,
    engine: AsyncCortexEngine,
    memory_name: str,
    query: str,
    *,
    top_k: int = 5,
    target_project: str = "langbase-enrichment",
) -> dict:
    """Search Langbase Memory and store results as CORTEX facts.

    Useful for importing external knowledge into CORTEX.

    Args:
        client: Langbase API client
        engine: CORTEX async engine
        memory_name: Langbase memory to search
        query: Search query
        top_k: Number of results
        target_project: CORTEX project to store enrichment facts

    Returns:
        Summary with counts
    """
    results = await client.retrieve_memory(memory_name, query, top_k=top_k)

    stored = 0
    for chunk in results:
        content = chunk.get("content") or chunk.get("text", "")
        if not content:
            continue

        score = chunk.get("score", 0.0)
        source = f"langbase:{memory_name}"

        await engine.store(
            project=target_project,
            content=content,
            fact_type="knowledge",
            tags=["langbase", "enrichment", memory_name],
            source=source,
            meta={"langbase_score": score, "query": query},
        )
        stored += 1

    logger.info(
        "Enrichment from Langbase: %d facts stored from memory '%s'",
        stored, memory_name,
    )
    return {
        "stored": stored,
        "source_memory": memory_name,
        "target_project": target_project,
        "query": query,
    }

"""CORTEX ADK Tools — Bridge between ADK agents and CortexEngine.

Wraps CortexEngine operations as plain Python functions that ADK agents
can call as tools. Each function is self-contained: it opens its own
engine connection, performs the operation, and returns a formatted string.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3

from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.adk.tools")

_DEFAULT_DB = os.path.expanduser("~/.cortex/cortex.db")


def _get_db_path() -> str:
    return os.environ.get("CORTEX_DB_PATH", _DEFAULT_DB)


# ─── Store ────────────────────────────────────────────────────────────


def adk_store(
    project: str,
    content: str,
    fact_type: str = "knowledge",
    tags: str = "[]",
    source: str = "",
) -> dict:
    """Store a fact in CORTEX sovereign memory.

    Args:
        project: Project namespace (e.g. 'cortex', 'naroa-2026').
        content: The fact content to store.
        fact_type: One of: knowledge, decision, error, rule, axiom, schema, idea, ghost, bridge.
        tags: JSON array of string tags (e.g. '["architecture", "adk"]').
        source: Optional source attribution.

    Returns:
        A dict with status and fact_id.
    """
    try:
        parsed_tags = json.loads(tags) if tags else []
    except (json.JSONDecodeError, TypeError):
        parsed_tags = []

    engine = CortexEngine(_get_db_path(), auto_embed=False)
    try:
        engine.init_db()
        fact_id = engine.store(
            project=project,
            content=content,
            fact_type=fact_type,
            tags=parsed_tags,
            confidence="stated",
            source=source or None,
        )
        return {"status": "success", "fact_id": fact_id, "project": project}
    except (sqlite3.Error, OSError, RuntimeError) as exc:
        logger.error("ADK store failed: %s", exc)
        return {"status": "error", "message": str(exc)}
    finally:
        engine.close()


# ─── Search ───────────────────────────────────────────────────────────


def adk_search(
    query: str,
    project: str = "",
    top_k: int = 5,
) -> dict:
    """Search CORTEX memory using hybrid semantic + text search.

    Args:
        query: Natural language search query.
        project: Optional project filter.
        top_k: Number of results to return (1-20).

    Returns:
        A dict with status and results list.
    """
    engine = CortexEngine(_get_db_path(), auto_embed=False)
    try:
        engine.init_db()
        results = engine.search(
            query=query,
            project=project or None,
            top_k=min(max(top_k, 1), 20),
        )

        if not results:
            return {"status": "success", "results": [], "message": "No results found."}

        formatted = []
        for r in results:
            formatted.append({
                "fact_id": r.fact_id,
                "score": round(r.score, 3),
                "project": r.project,
                "fact_type": r.fact_type,
                "content": r.content,
            })

        return {"status": "success", "results": formatted, "count": len(formatted)}
    except (sqlite3.Error, OSError, RuntimeError) as exc:
        logger.error("ADK search failed: %s", exc)
        return {"status": "error", "message": str(exc)}
    finally:
        engine.close()


# ─── Status ───────────────────────────────────────────────────────────


def adk_status() -> dict:
    """Get CORTEX system status and statistics.

    Returns:
        A dict with system stats including fact counts, projects, and DB size.
    """
    engine = CortexEngine(_get_db_path(), auto_embed=False)
    try:
        engine.init_db()
        stats = engine.stats()
        return {"status": "success", **stats}
    except (sqlite3.Error, OSError, RuntimeError) as exc:
        logger.error("ADK status failed: %s", exc)
        return {"status": "error", "message": str(exc)}
    finally:
        engine.close()


# ─── Ledger Verify ────────────────────────────────────────────────────


def adk_ledger_verify() -> dict:
    """Verify the integrity of the CORTEX immutable transaction ledger.

    Performs a full hash-chain verification and Merkle checkpoint audit.

    Returns:
        A dict with verification results.
    """
    from cortex.engine.ledger import ImmutableLedger

    engine = CortexEngine(_get_db_path(), auto_embed=False)
    try:
        engine.init_db()
        ledger = ImmutableLedger(engine._conn)
        report = ledger.verify_integrity()
        return {
            "status": "success",
            "valid": report.get("valid", False),
            "transactions_checked": report.get("tx_checked", 0),
            "roots_checked": report.get("roots_checked", 0),
            "violations": report.get("violations", []),
        }
    except (sqlite3.Error, OSError, RuntimeError) as exc:
        logger.error("ADK ledger verify failed: %s", exc)
        return {"status": "error", "message": str(exc)}
    finally:
        engine.close()


# ─── Tool Registry ────────────────────────────────────────────────────

ALL_TOOLS = [adk_store, adk_search, adk_status, adk_ledger_verify]
"""All available CORTEX tools for ADK agents."""

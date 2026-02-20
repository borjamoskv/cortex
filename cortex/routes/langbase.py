# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v4.2 — Langbase Router.

REST endpoints for Langbase integration:
- /v1/langbase/pipe/run   — Run Pipe with CORTEX context
- /v1/langbase/sync       — Sync facts to Langbase Memory
- /v1/langbase/search     — Search Langbase Memory (proxy)
- /v1/langbase/status     — Connection status
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from cortex.api_deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.config import LANGBASE_API_KEY, LANGBASE_BASE_URL
from cortex.engine_async import AsyncCortexEngine
from cortex.langbase.client import LangbaseClient, LangbaseError
from cortex.langbase.pipe import run_with_cortex_context
from cortex.langbase.sync import enrich_from_langbase, sync_to_langbase

logger = logging.getLogger("cortex.routes.langbase")

router = APIRouter(prefix="/v1/langbase", tags=["langbase"])


# ─── Request / Response Models ───────────────────────────────────────


class PipeRunRequest(BaseModel):
    """Run a Langbase Pipe with CORTEX context."""

    pipe_name: str = Field(..., min_length=1, max_length=256, description="Langbase Pipe name")
    query: str = Field(..., min_length=1, max_length=8192, description="User query / prompt")
    project: str | None = Field(None, description="Filter CORTEX facts by project")
    top_k: int = Field(10, ge=1, le=50, description="Number of CORTEX facts for context")
    thread_id: str | None = Field(None, description="Langbase thread ID for conversation")


class SyncRequest(BaseModel):
    """Sync CORTEX facts to Langbase Memory."""

    project: str = Field(..., min_length=1, max_length=256, description="CORTEX project to sync")
    memory_name: str | None = Field(None, description="Override Langbase memory name")
    limit: int = Field(500, ge=1, le=2000, description="Max facts to sync")


class MemorySearchRequest(BaseModel):
    """Search Langbase Memory."""

    memory_name: str = Field(..., min_length=1, description="Langbase memory name")
    query: str = Field(..., min_length=1, max_length=4096, description="Search query")
    top_k: int = Field(5, ge=1, le=50, description="Number of results")


# ─── Dependency ──────────────────────────────────────────────────────


def _get_client() -> LangbaseClient:
    """Get a Langbase client, fail if not configured."""
    if not LANGBASE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Langbase not configured. Set LANGBASE_API_KEY env variable.",
        )
    return LangbaseClient(api_key=LANGBASE_API_KEY, base_url=LANGBASE_BASE_URL)


# ─── Endpoints ───────────────────────────────────────────────────────


@router.post("/pipe/run")
async def langbase_pipe_run(
    req: PipeRunRequest,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> dict:
    """Run a Langbase Pipe enriched with CORTEX memory context.

    Searches CORTEX for relevant facts, injects them as context,
    and runs the specified Langbase Pipe.
    """
    client = _get_client()
    try:
        result = await run_with_cortex_context(
            client=client,
            engine=engine,
            pipe_name=req.pipe_name,
            query=req.query,
            project=req.project or auth.tenant_id,
            top_k=req.top_k,
            thread_id=req.thread_id,
        )
        return result
    except LangbaseError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.detail) from None
    except (OSError, ValueError, KeyError):
        logger.exception("Langbase pipe run failed")
        raise HTTPException(status_code=500, detail="Pipe execution failed") from None
    finally:
        await client.close()


@router.post("/sync")
async def langbase_sync(
    req: SyncRequest,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> dict:
    """Sync CORTEX facts to Langbase Memory.

    Exports facts from a project as markdown documents
    into a Langbase Memory set for cloud RAG.
    """
    # Tenant isolation: only sync own projects
    if req.project != auth.tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Can only sync facts from your own tenant project",
        )

    client = _get_client()
    try:
        result = await sync_to_langbase(
            client=client,
            engine=engine,
            project=req.project,
            memory_name=req.memory_name,
            limit=req.limit,
        )
        return result
    except LangbaseError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.detail) from None
    except (OSError, ValueError, KeyError):
        logger.exception("Langbase sync failed")
        raise HTTPException(status_code=500, detail="Sync failed") from None
    finally:
        await client.close()


@router.post("/search")
async def langbase_memory_search(
    req: MemorySearchRequest,
    auth: AuthResult = Depends(require_permission("read")),
) -> dict:
    """Search a Langbase Memory set (RAG proxy).

    Performs semantic search against a Langbase Memory
    and returns matching chunks with scores.
    """
    client = _get_client()
    try:
        results = await client.retrieve_memory(
            name=req.memory_name,
            query=req.query,
            top_k=req.top_k,
        )
        return {"results": results, "count": len(results), "memory": req.memory_name}
    except LangbaseError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.detail) from None
    except (OSError, ValueError, KeyError):
        logger.exception("Langbase search failed")
        raise HTTPException(status_code=500, detail="Memory search failed") from None
    finally:
        await client.close()


@router.get("/status")
async def langbase_status(
    auth: AuthResult = Depends(require_permission("read")),
) -> dict:
    """Check Langbase API connectivity and resource counts."""
    if not LANGBASE_API_KEY:
        return {
            "configured": False,
            "connected": False,
            "message": "LANGBASE_API_KEY not set",
        }

    client = _get_client()
    try:
        status = await client.status()
        status["configured"] = True
        return status
    finally:
        await client.close()

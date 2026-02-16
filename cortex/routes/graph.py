"""
CORTEX v4.0 - Graph Router.

Exposes entity graph endpoints for UI and external consumers.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from starlette.concurrency import run_in_threadpool
from cortex.auth import AuthResult, require_permission
from cortex.api_deps import get_engine
from cortex.engine import CortexEngine
from cortex.graph import get_graph as _get_graph_sync

router = APIRouter(tags=["graph"])
logger = logging.getLogger("uvicorn.error")


@router.get("/v1/graph/{project}")
async def get_graph(
    project: str,
    limit: int = Query(50, ge=1, le=500),
    auth: AuthResult = Depends(require_permission("read")),
    engine: CortexEngine = Depends(get_engine),
) -> dict:
    """Get entity graph for a specific project."""
    if auth.tenant_id != "default" and project != auth.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden: Access to this project is denied")

    try:
        conn = await engine.get_conn()
        result = await run_in_threadpool(_get_graph_sync, conn, project, limit)
        return result
    except Exception as e:
        logger.error("Graph unavailable: %s", e)
        raise HTTPException(status_code=500, detail="Graph unavailable")


@router.get("/v1/graph")
async def get_graph_all(
    limit: int = Query(50, ge=1, le=500),
    auth: AuthResult = Depends(require_permission("read")),
    engine: CortexEngine = Depends(get_engine),
) -> dict:
    """Get entity graph across all projects."""
    try:
        conn = await engine.get_conn()
        result = await run_in_threadpool(_get_graph_sync, conn, None, limit)
        return result
    except Exception as e:
        logger.error("Graph unavailable: %s", e)
        raise HTTPException(status_code=500, detail="Graph unavailable")

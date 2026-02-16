"""
CORTEX v4.0 — Graph Router.

Exposes entity graph endpoints for UI and external consumers.
"""

import sqlite3
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from starlette.concurrency import run_in_threadpool
from cortex.auth import AuthResult, require_permission
from cortex import api_state
from cortex.graph import get_graph as _get_graph_impl

router = APIRouter(tags=["graph"])
logger = logging.getLogger("uvicorn.error")


@router.get("/v1/graph/{project}")
async def get_graph(
    project: str,
    limit: int = Query(50, ge=1, le=500),
    auth: AuthResult = Depends(require_permission("read")),
) -> dict:
    """Get entity graph for a specific project."""
    # Tenant Isolation
    if auth.tenant_id != "default" and project != auth.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden: Access to this project is denied")

    try:
        conn = api_state.engine.conn
        result = await run_in_threadpool(_get_graph_impl, conn, project=project, limit=limit)
        return result
    except sqlite3.Error as e:
        logger.error("Graph unavailable: %s", e)
        raise HTTPException(status_code=500, detail="Graph unavailable")


@router.get("/v1/graph")
async def get_graph_all(
    limit: int = Query(50, ge=1, le=500),
    auth: AuthResult = Depends(require_permission("read")),
) -> dict:
    """Get entity graph across all projects."""
    try:
        conn = api_state.engine.conn
        result = await run_in_threadpool(_get_graph_impl, conn, project=None, limit=limit)
        return result
    except sqlite3.Error as e:
        logger.error("Graph unavailable: %s", e)
        raise HTTPException(status_code=500, detail="Graph unavailable")

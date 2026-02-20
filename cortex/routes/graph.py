"""
CORTEX v4.0 - Graph Router.

Exposes entity graph endpoints for UI and external consumers.
"""

import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from cortex.api_deps import get_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine import CortexEngine
from cortex.graph import get_graph as _get_graph
from cortex.i18n import get_trans

router = APIRouter(tags=["graph"])
logger = logging.getLogger("uvicorn.error")


@router.get("/v1/graph/{project}")
async def get_graph(
    project: str,
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    auth: AuthResult = Depends(require_permission("read")),
    engine: CortexEngine = Depends(get_engine),
) -> dict:
    """Get entity graph for a specific project."""
    lang = request.headers.get("Accept-Language", "en")
    if auth.tenant_id != "default" and project != auth.tenant_id:
        raise HTTPException(status_code=403, detail=get_trans("error_graph_forbidden", lang))

    try:
        conn = await engine.get_conn()
        return await _get_graph(conn, project, limit)
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.error("Graph unavailable: %s", e)
        raise HTTPException(status_code=500, detail=get_trans("error_graph_unavailable", lang)) from None


@router.get("/v1/graph")
async def get_graph_all(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    auth: AuthResult = Depends(require_permission("read")),
    engine: CortexEngine = Depends(get_engine),
) -> dict:
    """Get entity graph across all projects."""
    try:
        conn = await engine.get_conn()
        return await _get_graph(conn, None, limit)
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.error("Graph unavailable: %s", e)
        lang = request.headers.get("Accept-Language", "en")
        raise HTTPException(status_code=500, detail=get_trans("error_graph_unavailable", lang)) from None

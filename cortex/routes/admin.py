"""
CORTEX v4.0 - Admin Router.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from cortex import api_state
from cortex.api_deps import get_engine
from cortex.auth import AuthResult, get_auth_manager, require_permission
from cortex.engine import CortexEngine
from cortex.models import StatusResponse
from cortex.sync import export_to_json

router = APIRouter(tags=["admin"])
logger = logging.getLogger("uvicorn.error")


@router.get("/v1/projects/{project}/export")
async def export_project(
    project: str,
    path: Optional[str] = Query(None),
    fmt: str = Query("json", alias="format"),
) -> dict:
    """Export a project to a JSON file (with path validation)."""
    if fmt != "json":
        raise HTTPException(status_code=400, detail="Only JSON format supported via API")

    if path:
        if any(c in path for c in ("\0", "\r", "\n", "\t")):
            raise HTTPException(status_code=400, detail="Invalid characters in path")

        from pathlib import Path

        try:
            base_dir = Path.cwd().resolve()
            target_path = Path(path).resolve()
            if not str(target_path).startswith(str(base_dir)):
                raise HTTPException(
                    status_code=400, detail="Path must be relative and within the workspace"
                )
        except (ValueError, RuntimeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid path: {e}")

    try:
        # export_to_json is sync, uses its own connection
        out_path = await run_in_threadpool(export_to_json, api_state.engine, project, path)
        return {"message": f"Exported project '{project}' to {out_path}", "path": str(out_path)}
    except Exception as e:
        logger.error("Export failed: %s", e)
        raise HTTPException(status_code=500, detail="Export failed")


@router.get("/v1/status", response_model=StatusResponse)
async def status(
    auth: AuthResult = Depends(require_permission("read")),
    engine: CortexEngine = Depends(get_engine),
) -> StatusResponse:
    """Get engine status and statistics."""
    try:
        stats = await engine.stats()
        return StatusResponse(
            version="4.0.0a1",
            total_facts=stats["total_facts"],
            active_facts=stats["active_facts"],
            deprecated=stats["deprecated_facts"],
            projects=stats["project_count"],
            embeddings=stats["embeddings"],
            transactions=stats["transactions"],
            db_size_mb=stats["db_size_mb"],
        )
    except Exception as e:
        logger.error("Status unavailable: %s", e)
        raise HTTPException(status_code=500, detail="Status unavailable")


@router.post("/v1/admin/keys")
async def create_api_key(
    name: str = Query(...),
    tenant_id: str = Query("default"),
    authorization: str = Header(None),
) -> dict:
    """Create a new API key. First key requires no auth (bootstrap)."""
    manager = api_state.auth_manager or get_auth_manager()
    keys = manager.list_keys()
    if keys:
        if not authorization:
            raise HTTPException(status_code=401, detail="Auth required")
        parts = authorization.split(" ", 1)
        if len(parts) != 2:
            raise HTTPException(status_code=401, detail="Invalid auth")
        result = api_state.auth_manager.authenticate(parts[1])
        if not result.authenticated:
            raise HTTPException(status_code=401, detail=result.error)
        if "admin" not in result.permissions:
            raise HTTPException(status_code=403, detail="Admin permission required")

    raw_key, api_key = manager.create_key(
        name=name,
        tenant_id=tenant_id,
        permissions=["read", "write", "admin"],
    )
    return {
        "key": raw_key,
        "name": api_key.name,
        "prefix": api_key.key_prefix,
        "tenant_id": api_key.tenant_id,
        "message": "Save this key - it will NOT be shown again.",
    }


@router.get("/v1/admin/keys")
async def list_api_keys(auth: AuthResult = Depends(require_permission("admin"))) -> list[dict]:
    """List all API keys (hashed, never reveals raw key)."""
    manager = api_state.auth_manager or get_auth_manager()
    keys = manager.list_keys()
    return [
        {
            "id": k.id,
            "name": k.name,
            "prefix": k.key_prefix,
            "tenant_id": k.tenant_id,
            "permissions": k.permissions,
            "is_active": k.is_active,
            "created_at": k.created_at,
            "last_used": k.last_used,
        }
        for k in keys
    ]

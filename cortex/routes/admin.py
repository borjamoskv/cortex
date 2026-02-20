"""
CORTEX v4.0 - Admin Router.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool

from cortex import __version__, api_state
from cortex.api_deps import get_engine
from cortex.auth import AuthResult, get_auth_manager, require_permission
from cortex.engine import CortexEngine
from cortex.i18n import get_trans
from cortex.models import StatusResponse
from cortex.sync import export_to_json

router = APIRouter(tags=["admin"])
logger = logging.getLogger("uvicorn.error")


@router.get("/v1/projects/{project}/export")
async def export_project(
    project: str,
    request: Request,
    path: str | None = Query(None),
    fmt: str = Query("json", alias="format"),
) -> dict:
    """Export a project to a JSON file (with path validation)."""
    lang = request.headers.get("Accept-Language", "en")
    if fmt != "json":
        raise HTTPException(status_code=400, detail=get_trans("error_json_only", lang))

    if path:
        if any(c in path for c in ("\0", "\r", "\n", "\t")):
            raise HTTPException(status_code=400, detail=get_trans("error_invalid_path_chars", lang))

        from pathlib import Path

        try:
            base_dir = Path.cwd().resolve()
            target_path = Path(path).resolve()
            if not str(target_path).startswith(str(base_dir)):
                raise HTTPException(
                    status_code=400, detail=get_trans("error_path_workspace", lang)
                )
        except (ValueError, RuntimeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid path: {e}") from None

    try:
        # export_to_json is sync, uses its own connection
        out_path = await run_in_threadpool(export_to_json, api_state.engine, project, path)
        return {"message": f"Exported project '{project}' to {out_path}", "path": str(out_path)}
    except (OSError, ValueError, KeyError) as e:
        logger.error("Export failed: %s", e)
        raise HTTPException(status_code=500, detail=get_trans("error_export_failed", lang)) from None


@router.get("/v1/status", response_model=StatusResponse)
async def status(
    request: Request,
    auth: AuthResult = Depends(require_permission("read")),
    engine: CortexEngine = Depends(get_engine),
) -> StatusResponse:
    """Get engine status and statistics."""
    lang = request.headers.get("Accept-Language", "en")
    try:
        stats = engine.stats()
        return StatusResponse(
            version=__version__,
            total_facts=stats["total_facts"],
            active_facts=stats["active_facts"],
            deprecated=stats["deprecated_facts"],
            projects=stats["project_count"],
            embeddings=stats["embeddings"],
            transactions=stats["transactions"],
            db_size_mb=stats["db_size_mb"],
        )
    except (OSError, ValueError, KeyError) as e:
        logger.error("Status unavailable: %s", e)
        raise HTTPException(status_code=500, detail=get_trans("error_status_unavailable", lang)) from None


@router.post("/v1/admin/keys")
async def create_api_key(
    request: Request,
    name: str = Query(...),
    tenant_id: str = Query("default"),
    authorization: str = Header(None),
) -> dict:
    """Create a new API key. First key requires no auth (bootstrap)."""
    lang = request.headers.get("Accept-Language", "en")
    manager = api_state.auth_manager or get_auth_manager()
    keys = manager.list_keys()
    if keys:
        if not authorization:
            raise HTTPException(status_code=401, detail=get_trans("error_auth_required", lang))
        parts = authorization.split(" ", 1)
        if len(parts) != 2:
            raise HTTPException(status_code=401, detail=get_trans("error_invalid_key_format", lang))
        result = api_state.auth_manager.authenticate(parts[1])
        if not result.authenticated:
            error_msg = get_trans("error_invalid_revoked_key", lang) if result.error else result.error
            raise HTTPException(status_code=401, detail=error_msg)
        if "admin" not in result.permissions:
            detail = get_trans("error_missing_permission", lang).format(permission="admin")
            raise HTTPException(status_code=403, detail=detail)

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


@router.post("/v1/handoff")
async def handoff_generate(
    request: Request,
    engine: CortexEngine = Depends(get_engine),
) -> dict:
    """Generate a session handoff with hot context."""
    from cortex.handoff import generate_handoff, save_handoff

    body = {}
    try:
        body = await request.json()
    except (OSError, ValueError, KeyError):
        pass

    session_meta = body.get("session", None)
    data = await generate_handoff(engine, session_meta=session_meta)
    save_handoff(data)
    return data


"""
CORTEX v4.0 — Daemon Router.
"""

from fastapi import APIRouter, Depends

from cortex.auth import AuthResult, require_permission

router = APIRouter(tags=["daemon"])


@router.get("/v1/daemon/status")
async def daemon_status(auth: AuthResult = Depends(require_permission("read"))) -> dict:
    """Get last daemon watchdog check results."""
    from cortex.daemon import MoskvDaemon

    status = MoskvDaemon.load_status()
    if not status:
        return {"status": "no_data", "message": "Daemon has not run yet."}
    return status

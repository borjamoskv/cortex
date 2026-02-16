"""
CORTEX v4.0 — Dashboard Router.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from cortex.auth import AuthResult, require_permission

router = APIRouter(tags=["dashboard"])

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    auth: AuthResult = Depends(require_permission("read")),
) -> str:
    """Serve the embedded memory dashboard."""
    from cortex.dashboard import get_dashboard_html
    return get_dashboard_html()

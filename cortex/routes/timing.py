"""
CORTEX v4.0 — Timing Router.
"""

import logging
import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from cortex import api_state
from cortex.auth import AuthResult, require_permission
from cortex.models import HeartbeatRequest, TimeSummaryResponse

router = APIRouter(tags=["timing"])
logger = logging.getLogger("uvicorn.error")


@router.post("/v1/heartbeat")
async def record_heartbeat(
    req: HeartbeatRequest,
    auth: AuthResult = Depends(require_permission("write")),
) -> dict:
    """Record an activity heartbeat for automatic time tracking."""
    # Tenant Isolation
    if auth.tenant_id != "default" and req.project != auth.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden: Project matches your tenant ID")

    try:
        hb_id = await run_in_threadpool(
            api_state.tracker.heartbeat,
            project=req.project,
            entity=req.entity,
            category=req.category,
            branch=req.branch,
            language=req.language,
            meta=req.meta,
        )
        await run_in_threadpool(api_state.tracker.flush)
        return {"id": hb_id, "status": "recorded"}
    except sqlite3.Error as e:
        logger.error("Heartbeat failed: %s", e)
        raise HTTPException(status_code=500, detail="Heartbeat failed")


@router.get("/v1/time/today", response_model=TimeSummaryResponse)
async def time_today(
    project: Optional[str] = Query(None),
    auth: AuthResult = Depends(require_permission("read")),
) -> TimeSummaryResponse:
    """Get today's time tracking summary."""
    # Tenant Isolation
    if auth.tenant_id != "default":
        if project and project != auth.tenant_id:
            raise HTTPException(
                status_code=403, detail="Forbidden: Access to this project is denied"
            )
        project = auth.tenant_id

    try:
        summary = await run_in_threadpool(api_state.tracker.today, project=project)
        return TimeSummaryResponse(
            total_seconds=summary.total_seconds,
            total_hours=summary.total_hours,
            by_category=summary.by_category,
            by_project=summary.by_project,
            entries=summary.entries,
            heartbeats=summary.heartbeats,
            top_entities=[[e, c] for e, c in summary.top_entities],
        )
    except sqlite3.Error as e:
        logger.error("Time summary failed: %s", e)
        raise HTTPException(status_code=500, detail="Time summary failed")


@router.get("/v1/time", response_model=TimeSummaryResponse)
async def time_report(
    project: Optional[str] = Query(None),
    days: int = Query(7),
    auth: AuthResult = Depends(require_permission("read")),
) -> TimeSummaryResponse:
    """Get time tracking report for the last N days."""
    # Tenant Isolation
    if auth.tenant_id != "default":
        if project and project != auth.tenant_id:
            raise HTTPException(
                status_code=403, detail="Forbidden: Access to this project is denied"
            )
        project = auth.tenant_id

    try:
        summary = await run_in_threadpool(api_state.tracker.report, project=project, days=days)
        return TimeSummaryResponse(
            total_seconds=summary.total_seconds,
            total_hours=summary.total_hours,
            by_category=summary.by_category,
            by_project=summary.by_project,
            entries=summary.entries,
            heartbeats=summary.heartbeats,
            top_entities=[[e, c] for e, c in summary.top_entities],
        )
    except sqlite3.Error as e:
        logger.error("Time report failed: %s", e)
        raise HTTPException(status_code=500, detail="Time report failed")


@router.get("/v1/time/history")
async def get_time_history(
    days: int = Query(7, ge=1, le=365),
    auth: AuthResult = Depends(require_permission("read")),
) -> list:
    """Get daily time history."""
    try:
        return await run_in_threadpool(api_state.tracker.daily, days=days)
    except sqlite3.Error as e:
        logger.error("Time history failed: %s", e)
        raise HTTPException(status_code=500, detail="Time history failed")

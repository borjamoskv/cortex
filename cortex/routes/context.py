"""
CORTEX v4.0 — Context Engine API Route.

Endpoints for ambient context inference, raw signals, and snapshot history.
"""

import logging

from fastapi import APIRouter, Depends, Query, Request

from cortex.api_deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.context.collector import ContextCollector
from cortex.context.inference import ContextInference
from cortex.engine_async import AsyncCortexEngine
from cortex.models import (
    ContextSignalModel,
    ContextSnapshotResponse,
    ProjectScoreModel,
)

router = APIRouter(prefix="/v1/context", tags=["context"])
logger = logging.getLogger("uvicorn.error")


@router.get("/infer", response_model=ContextSnapshotResponse)
async def infer_context(
    request: Request,
    persist: bool = Query(True, description="Persist snapshot to DB"),
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> ContextSnapshotResponse:
    """Run ambient context inference and return the current context snapshot."""
    from cortex import config

    async with engine.session() as conn:
        collector = ContextCollector(
            conn=conn,
            max_signals=config.CONTEXT_MAX_SIGNALS,
            workspace_dir=config.CONTEXT_WORKSPACE_DIR,
            git_enabled=config.CONTEXT_GIT_ENABLED,
        )
        signals = await collector.collect_all()

        inference = ContextInference(conn=conn if persist else None)
        if persist:
            result = await inference.infer_and_persist(signals)
        else:
            result = inference.infer(signals)

    return ContextSnapshotResponse(
        active_project=result.active_project,
        confidence=result.confidence,
        signals_used=result.signals_used,
        summary=result.summary,
        top_signals=[
            ContextSignalModel(**s.to_dict()) for s in result.top_signals
        ],
        projects_ranked=[
            ProjectScoreModel(project=p, score=round(s, 4))
            for p, s in result.projects_ranked
        ],
    )


@router.get("/signals", response_model=list[ContextSignalModel])
async def list_signals(
    request: Request,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[ContextSignalModel]:
    """List raw ambient signals without running inference."""
    from cortex import config

    async with engine.session() as conn:
        collector = ContextCollector(
            conn=conn,
            max_signals=config.CONTEXT_MAX_SIGNALS,
            workspace_dir=config.CONTEXT_WORKSPACE_DIR,
            git_enabled=config.CONTEXT_GIT_ENABLED,
        )
        signals = await collector.collect_all()

    return [ContextSignalModel(**s.to_dict()) for s in signals]


@router.get("/history", response_model=list[dict])
async def context_history(
    request: Request,
    limit: int = Query(10, ge=1, le=100),
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[dict]:
    """Retrieve past context inference snapshots."""
    async with engine.session() as conn:
        inference = ContextInference(conn=conn)
        return await inference.get_history(limit=limit)

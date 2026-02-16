"""
CORTEX v4.0 — MEJORAlo Router.

API endpoints for the MEJORAlo v7.3 protocol.
"""

from typing import List

from fastapi import APIRouter, Depends, Query

from cortex.api_deps import get_engine
from cortex.auth import require_permission
from cortex.engine import CortexEngine
from cortex.mejoralo import MejoraloEngine
from cortex.models import (
    DimensionResultModel,
    MejoraloScanRequest,
    MejoraloScanResponse,
    MejoraloSessionRequest,
    MejoraloSessionResponse,
    MejoraloShipRequest,
    MejoraloShipResponse,
    ShipSealModel,
)

router = APIRouter(prefix="/v1/mejoralo", tags=["mejoralo"])


@router.post("/scan", response_model=MejoraloScanResponse)
async def scan_project(
    request: MejoraloScanRequest,
    engine: CortexEngine = Depends(get_engine),
    _=Depends(require_permission("read")),
):
    """Execute X-Ray 13D scan on a project."""
    mejoralo = MejoraloEngine(engine)
    result = mejoralo.scan(request.project, request.path, deep=request.deep)
    return MejoraloScanResponse(
        project=result.project,
        score=result.score,
        stack=result.stack,
        dimensions=[
            DimensionResultModel(name=d.name, score=d.score, weight=d.weight, findings=d.findings)
            for d in result.dimensions
        ],
        dead_code=result.dead_code,
        total_files=result.total_files,
        total_loc=result.total_loc,
    )


@router.post("/record", response_model=MejoraloSessionResponse)
async def record_session(
    request: MejoraloSessionRequest,
    engine: CortexEngine = Depends(get_engine),
    _=Depends(require_permission("write")),
):
    """Record a MEJORAlo audit session in the ledger."""
    mejoralo = MejoraloEngine(engine)
    fact_id = mejoralo.record_session(
        project=request.project,
        score_before=request.score_before,
        score_after=request.score_after,
        actions=request.actions,
    )
    return MejoraloSessionResponse(
        fact_id=fact_id,
        project=request.project,
        delta=request.score_after - request.score_before,
    )


@router.get("/history", response_model=List[dict])
async def get_history(
    project: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
    engine: CortexEngine = Depends(get_engine),
    _=Depends(require_permission("read")),
):
    """Retrieve MEJORAlo session history for a project."""
    mejoralo = MejoraloEngine(engine)
    return mejoralo.history(project=project, limit=limit)


@router.post("/ship", response_model=MejoraloShipResponse)
async def ship_gate(
    request: MejoraloShipRequest,
    engine: CortexEngine = Depends(get_engine),
    _=Depends(require_permission("read")),
):
    """Validate the 7 Seals for production readiness."""
    mejoralo = MejoraloEngine(engine)
    result = mejoralo.ship_gate(request.project, request.path)
    return MejoraloShipResponse(
        project=result.project,
        ready=result.ready,
        seals=[ShipSealModel(name=s.name, passed=s.passed, detail=s.detail) for s in result.seals],
        passed=result.passed,
        total=result.total,
    )

"""
CORTEX v4.0 — Mission Orchestration Router.
"""

from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from cortex.api_deps import get_engine
from cortex.engine import CortexEngine
from cortex.launchpad import MissionOrchestrator
from cortex.models import MissionLaunchRequest, MissionResponse
from cortex.auth import require_permission

router = APIRouter(prefix="/v1/missions", tags=["missions"])

@router.post("/launch", response_model=MissionResponse)
async def launch_mission(
    request: MissionLaunchRequest,
    engine: CortexEngine = Depends(get_engine),
    _ = Depends(require_permission("write"))
):
    """Launch a new swarm mission through the CORTEX Launchpad."""
    orchestrator = MissionOrchestrator(engine)
    result = orchestrator.launch(
        project=request.project,
        goal=request.goal,
        formation=request.formation,
        agents=request.agents
    )
    return result

@router.get("/", response_model=List[dict])
async def list_missions(
    project: Optional[str] = Query(None),
    engine: CortexEngine = Depends(get_engine),
    _ = Depends(require_permission("read"))
):
    """List recent mission intents and reports from the ledger."""
    orchestrator = MissionOrchestrator(engine)
    return orchestrator.list_missions(project=project)

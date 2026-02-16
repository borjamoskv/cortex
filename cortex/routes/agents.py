"""
CORTEX v4.0 - Agents Router (Reputation Management).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from cortex.api_deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine_async import AsyncCortexEngine
from cortex.models import AgentRegisterRequest, AgentResponse

router = APIRouter(tags=["agents"])
logger = logging.getLogger("uvicorn.error")


@router.post("/v1/agents", response_model=AgentResponse)
async def register_agent(
    req: AgentRegisterRequest,
    auth: AuthResult = Depends(require_permission("admin")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> AgentResponse:
    """Register a new agent for Reputation-Weighted Consensus (Requires Admin)."""
    try:
        agent_id = await engine.register_agent(
            name=req.name,
            agent_type=req.agent_type,
            public_key=req.public_key or "",
            tenant_id=auth.tenant_id,
        )

        agent = await engine.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=500, detail="Failed to retrieve registered agent")

        return AgentResponse(
            agent_id=agent["id"],
            name=agent["name"],
            agent_type=agent["agent_type"],
            reputation_score=agent["reputation_score"],
            created_at=agent["created_at"],
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Agent registration failed")
        raise HTTPException(status_code=500, detail="Internal registration error")


@router.get("/v1/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> AgentResponse:
    """Get agent details and current reputation."""
    agent = await engine.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return AgentResponse(
        agent_id=agent["id"],
        name=agent["name"],
        agent_type=agent["agent_type"],
        reputation_score=agent["reputation_score"],
        created_at=agent["created_at"],
    )


@router.get("/v1/agents", response_model=list[AgentResponse])
async def list_agents(
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[AgentResponse]:
    """List all agents for the current tenant."""
    agents = await engine.list_agents(auth.tenant_id)
    return [
        AgentResponse(
            agent_id=a["id"],
            name=a["name"],
            agent_type=a["agent_type"],
            reputation_score=a["reputation_score"],
            created_at=a["created_at"],
        )
        for a in agents
    ]

"""
CORTEX v4.0 - Agents Router (Reputation Management).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from cortex.auth import AuthResult, require_permission
from cortex.models import AgentRegisterRequest, AgentResponse
from cortex.api_deps import get_engine
from cortex.engine import CortexEngine

router = APIRouter(tags=["agents"])
logger = logging.getLogger("uvicorn.error")

@router.post("/v1/agents", response_model=AgentResponse)
async def register_agent(
    req: AgentRegisterRequest,
    auth: AuthResult = Depends(require_permission("admin")),
    engine: CortexEngine = Depends(get_engine),
) -> AgentResponse:
    """Register a new agent for Reputation-Weighted Consensus (Requires Admin)."""
    try:
        agent_id = await engine.register_agent(
            name=req.name,
            agent_type=req.agent_type,
            public_key=req.public_key or "",
            tenant_id=auth.tenant_id,
        )

        conn = await engine.get_conn()
        cursor = await conn.execute(
            "SELECT id, name, agent_type, reputation_score, created_at FROM agents WHERE id = ?",
            (agent_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="Failed to retrieve registered agent")

        return AgentResponse(
            agent_id=row[0],
            name=row[1],
            agent_type=row[2],
            reputation_score=row[3],
            created_at=row[4],
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
    engine: CortexEngine = Depends(get_engine),
) -> AgentResponse:
    """Get agent details and current reputation."""
    conn = await engine.get_conn()
    cursor = await conn.execute(
        "SELECT id, name, agent_type, reputation_score, created_at FROM agents WHERE id = ?",
        (agent_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")

    return AgentResponse(
        agent_id=row[0],
        name=row[1],
        agent_type=row[2],
        reputation_score=row[3],
        created_at=row[4],
    )

@router.get("/v1/agents", response_model=list[AgentResponse])
async def list_agents(
    auth: AuthResult = Depends(require_permission("read")),
    engine: CortexEngine = Depends(get_engine),
) -> list[AgentResponse]:
    """List all agents for the current tenant."""
    conn = await engine.get_conn()
    cursor = await conn.execute(
        "SELECT id, name, agent_type, reputation_score, created_at FROM agents WHERE tenant_id = ?",
        (auth.tenant_id,),
    )
    rows = await cursor.fetchall()
    return [
        AgentResponse(
            agent_id=r[0],
            name=r[1],
            agent_type=r[2],
            reputation_score=r[3],
            created_at=r[4],
        )
        for r in rows
    ]

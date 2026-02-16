"""
CORTEX v4.0 - Facts Router.
Modularized fact operations: store, recall, deprecate, vote.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from cortex.auth import AuthResult, require_permission
from cortex.models import (
    StoreRequest, StoreResponse, FactResponse,
    VoteRequest, VoteResponse, VoteV2Request
)
from cortex.api_deps import get_engine
from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.api.facts")
router = APIRouter(tags=["facts"])


@router.post("/v1/facts", response_model=StoreResponse)
async def store_fact(
    req: StoreRequest,
    auth: AuthResult = Depends(require_permission("write")),
    engine: CortexEngine = Depends(get_engine),
) -> StoreResponse:
    """Store a fact with automatic tenant isolation."""
    fact_id = await engine.store(
        project=auth.tenant_id,
        content=req.content,
        fact_type=req.fact_type,
        tags=req.tags,
        meta=req.metadata,
    )
    return StoreResponse(
        fact_id=fact_id,
        project=auth.tenant_id,
        message=f"Fact #{fact_id} stored in project '{auth.tenant_id}'"
    )


@router.get("/v1/projects/{project}/facts", response_model=List[FactResponse])
async def recall_project(
    project: str,
    limit: Optional[int] = Query(None, ge=1, le=1000),
    auth: AuthResult = Depends(require_permission("read")),
    engine: CortexEngine = Depends(get_engine),
) -> List[FactResponse]:
    """Recall facts for a specific project with tenant isolation."""
    if project != auth.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden: Namespace mismatch")

    facts = await engine.recall(project=project, limit=limit)

    return [
        FactResponse(
            id=f.id,
            project=f.project,
            content=f.content,
            fact_type=f.fact_type,
            tags=f.tags,
            created_at=f.created_at,
            updated_at=f.updated_at,
            valid_from=f.valid_from,
            valid_until=f.valid_until,
            metadata=f.meta if f.meta else None,
            confidence=f.confidence,
            consensus_score=f.consensus_score,
            hash=f.hash,
            tx_id=f.tx_id,
        )
        for f in facts
    ]


@router.post("/v1/facts/{fact_id}/vote", response_model=VoteResponse)
async def cast_vote(
    fact_id: int,
    req: VoteRequest,
    auth: AuthResult = Depends(require_permission("write")),
    engine: CortexEngine = Depends(get_engine),
) -> VoteResponse:
    """Cast a consensus vote (verify/dispute) on a fact."""
    try:
        conn = await engine.get_conn()
        cursor = await conn.execute(
            "SELECT project FROM facts WHERE id = ?", (fact_id,)
        )
        row = await cursor.fetchone()
        project = row[0] if row else None

        if not project:
            raise HTTPException(status_code=404, detail=f"Fact #{fact_id} not found")
        if project != auth.tenant_id:
            raise HTTPException(status_code=403, detail="Forbidden: Fact belongs to another tenant")

        agent_id = auth.key_name or "api_agent"
        score = await engine.vote(fact_id, agent_id, req.value)

        cursor = await conn.execute(
            "SELECT confidence FROM facts WHERE id = ?", (fact_id,)
        )
        row = await cursor.fetchone()
        confidence = row[0] if row else "unknown"

        return VoteResponse(
            fact_id=fact_id,
            agent=agent_id,
            vote=req.value,
            new_consensus_score=score,
            confidence=confidence
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during voting for fact #%d", fact_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/v1/facts/{fact_id}/vote-v2", response_model=VoteResponse)
async def cast_vote_v2(
    fact_id: int,
    req: VoteV2Request,
    auth: AuthResult = Depends(require_permission("write")),
    engine: CortexEngine = Depends(get_engine),
) -> VoteResponse:
    """Cast a reputation-weighted consensus vote (RWC)."""
    try:
        conn = await engine.get_conn()
        cursor = await conn.execute(
            "SELECT project FROM facts WHERE id = ?", (fact_id,)
        )
        row = await cursor.fetchone()
        project = row[0] if row else None

        if not project:
            raise HTTPException(status_code=404, detail=f"Fact #{fact_id} not found")
        if project != auth.tenant_id:
            raise HTTPException(status_code=403, detail="Forbidden: Fact belongs to another tenant")

        score = await engine.vote(
            fact_id=fact_id,
            agent=auth.key_name or "api_agent",
            value=req.vote,
            agent_id=req.agent_id,
        )

        cursor = await conn.execute(
            "SELECT confidence FROM facts WHERE id = ?", (fact_id,)
        )
        row = await cursor.fetchone()
        confidence = row[0] if row else "unknown"

        return VoteResponse(
            fact_id=fact_id,
            agent=req.agent_id,
            vote=req.vote,
            new_consensus_score=score,
            confidence=confidence
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("RWC Vote failed")
        raise HTTPException(status_code=500, detail="Internal voting error")


@router.get("/v1/facts/{fact_id}/votes", response_model=List[dict])
async def get_votes(
    fact_id: int,
    auth: AuthResult = Depends(require_permission("read")),
    engine: CortexEngine = Depends(get_engine),
) -> List[dict]:
    """Retrieve all votes for a specific fact (Tenant Isolated)."""
    conn = await engine.get_conn()
    cursor = await conn.execute(
        "SELECT project FROM facts WHERE id = ?", (fact_id,)
    )
    row = await cursor.fetchone()
    project = row[0] if row else None

    if not project:
        raise HTTPException(status_code=404, detail=f"Fact #{fact_id} not found")
    if project != auth.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # V2 votes
    cursor = await conn.execute(
        """SELECT 'v2' as type, v.vote, v.agent_id as agent, v.created_at, a.reputation_score
           FROM consensus_votes_v2 v
           JOIN agents a ON v.agent_id = a.id
           WHERE v.fact_id = ?""",
        (fact_id,),
    )
    v2_votes = await cursor.fetchall()

    # Legacy votes
    cursor = await conn.execute(
        """SELECT 'legacy' as type, vote, agent, timestamp as created_at, 0.0 as reputation_score
           FROM consensus_votes
           WHERE fact_id = ?""",
        (fact_id,),
    )
    legacy_votes = await cursor.fetchall()

    return [
        {
            "type": r[0],
            "vote": r[1],
            "agent": r[2],
            "timestamp": r[3],
            "reputation": r[4],
        }
        for r in (v2_votes + legacy_votes)
    ]


@router.delete("/v1/facts/{fact_id}")
async def deprecate_fact(
    fact_id: int,
    auth: AuthResult = Depends(require_permission("write")),
    engine: CortexEngine = Depends(get_engine),
) -> dict:
    """Soft-deprecate a fact (mark as invalid)."""
    conn = await engine.get_conn()
    cursor = await conn.execute(
        "SELECT project FROM facts WHERE id = ?", (fact_id,)
    )
    row = await cursor.fetchone()
    project = row[0] if row else None

    if not project:
        raise HTTPException(status_code=404, detail=f"Fact #{fact_id} not found")
    if project != auth.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    success = await engine.deprecate(fact_id, project)
    if not success:
        raise HTTPException(status_code=500, detail="Deprecation failed")

    return {"message": f"Fact #{fact_id} deprecated", "success": True}

"""
CORTEX v4.0 - Facts Router.
Modularized fact operations: store, recall, deprecate, vote.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from cortex.api_deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine_async import AsyncCortexEngine
from cortex.models import (
    FactResponse,
    StoreRequest,
    StoreResponse,
    VoteRequest,
    VoteResponse,
    VoteV2Request,
)

logger = logging.getLogger("cortex.api.facts")
router = APIRouter(tags=["facts"])


@router.post("/v1/facts", response_model=StoreResponse)
async def store_fact(
    req: StoreRequest,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
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
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> List[FactResponse]:
    """Recall facts for a specific project with tenant isolation."""
    if project != auth.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden: Namespace mismatch")

    facts = await engine.recall(project=project, limit=limit)

    return [
        FactResponse(
            id=f["id"],
            project=f["project"],
            content=f["content"],
            fact_type=f["fact_type"],
            tags=f["tags"],
            created_at=f["created_at"],
            updated_at=f["updated_at"],
            valid_from=f["valid_from"],
            valid_until=f["valid_until"],
            metadata=f["meta"] if f.get("meta") else None,
            confidence=f["confidence"],
            consensus_score=f["consensus_score"],
            hash=f.get("hash"),
            tx_id=f.get("tx_id"),
        )
        for f in facts
    ]


@router.post("/v1/facts/{fact_id}/vote", response_model=VoteResponse)
async def cast_vote(
    fact_id: int,
    req: VoteRequest,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> VoteResponse:
    """Cast a consensus vote (verify/dispute) on a fact."""
    try:
        fact = await engine.get_fact(fact_id)
        if not fact:
            raise HTTPException(status_code=404, detail=f"Fact #{fact_id} not found")
        
        if fact["project"] != auth.tenant_id:
            raise HTTPException(status_code=403, detail="Forbidden: Fact belongs to another tenant")

        agent_id = auth.key_name or "api_agent"
        score = await engine.vote(fact_id, agent_id, req.value)

        # Re-fetch for updated confidence
        updated_fact = await engine.get_fact(fact_id)
        confidence = updated_fact["confidence"] if updated_fact else "unknown"

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
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> VoteResponse:
    """Cast a reputation-weighted consensus vote (RWC)."""
    try:
        fact = await engine.get_fact(fact_id)
        if not fact:
            raise HTTPException(status_code=404, detail=f"Fact #{fact_id} not found")
        
        if fact["project"] != auth.tenant_id:
            raise HTTPException(status_code=403, detail="Forbidden: Fact belongs to another tenant")

        score = await engine.vote(
            fact_id=fact_id,
            agent=auth.key_name or "api_agent",
            value=req.vote,
            agent_id=req.agent_id,
        )

        # Re-fetch for updated confidence
        updated_fact = await engine.get_fact(fact_id)
        confidence = updated_fact["confidence"] if updated_fact else "unknown"

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
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> List[dict]:
    """Retrieve all votes for a specific fact (Tenant Isolated)."""
    fact = await engine.get_fact(fact_id)
    if not fact:
        raise HTTPException(status_code=404, detail=f"Fact #{fact_id} not found")
    
    if fact["project"] != auth.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    votes = await engine.get_votes(fact_id)

    return [
        {
            "type": r["type"],
            "vote": r["vote"],
            "agent": r["agent"],
            "timestamp": r["created_at"],
            "reputation": r["reputation_score"],
        }
        for r in votes
    ]


@router.delete("/v1/facts/{fact_id}")
async def deprecate_fact(
    fact_id: int,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> dict:
    """Soft-deprecate a fact (mark as invalid)."""
    fact = await engine.get_fact(fact_id)
    if not fact:
        raise HTTPException(status_code=404, detail=f"Fact #{fact_id} not found")
    
    if fact["project"] != auth.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    success = await engine.deprecate(fact_id, auth.tenant_id)
    if not success:
        raise HTTPException(status_code=500, detail="Deprecation failed")

    return {"message": f"Fact #{fact_id} deprecated", "success": True}

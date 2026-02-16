"""
CORTEX v4.0 — Facts Router.
Modularized fact operations: store, recall, deprecate, vote.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from starlette.concurrency import run_in_threadpool

from cortex import api_state
from cortex.auth import AuthResult, require_permission
from cortex.models import (
    StoreRequest, StoreResponse, FactResponse, 
    VoteRequest, VoteResponse, VoteV2Request
)

logger = logging.getLogger("cortex.api.facts")
router = APIRouter(tags=["facts"])


@router.post("/v1/facts", response_model=StoreResponse)
async def store_fact(
    req: StoreRequest,
    auth: AuthResult = Depends(require_permission("write")),
) -> StoreResponse:
    """Store a fact with automatic tenant isolation."""
    fact_id = await run_in_threadpool(
        api_state.engine.store,
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
) -> List[FactResponse]:
    """Recall facts for a specific project with tenant isolation."""
    if project != auth.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden: Namespace mismatch")

    facts = await run_in_threadpool(api_state.engine.recall, project=project, limit=limit)
    
    return [
        FactResponse(
            id=f.id,
            project=f.project,
            content=f.content,
            fact_type=f.fact_type,
            tags=f.tags,
            created_at=f.valid_from, # Using valid_from as created_at proxy
            valid_from=f.valid_from,
            valid_until=f.valid_until,
            metadata=f.meta if f.meta else None,
            confidence=f.confidence,
            consensus_score=f.consensus_score,
        )
        for f in facts
    ]


@router.post("/v1/facts/{fact_id}/vote", response_model=VoteResponse)
async def cast_vote(
    fact_id: int,
    req: VoteRequest,
    auth: AuthResult = Depends(require_permission("write")),
) -> VoteResponse:
    """Cast a consensus vote (verify/dispute) on a fact."""
    try:
        # Ownership check
        def _check_owner():
            with api_state.engine._get_conn() as conn:
                row = conn.execute("SELECT project FROM facts WHERE id = ?", (fact_id,)).fetchone()
                return row[0] if row else None
        
        project = await run_in_threadpool(_check_owner)
        if not project:
            raise HTTPException(status_code=404, detail=f"Fact #{fact_id} not found")
        if project != auth.tenant_id:
            raise HTTPException(status_code=403, detail="Forbidden: Fact belongs to another tenant")

        # Use auth identity for voting
        agent_id = auth.key_name or "api_agent"
        
        # Cast vote (req.value is 1, -1, or 0)
        score = await run_in_threadpool(api_state.engine.vote, fact_id, agent_id, req.value)
        
        # Get updated confidence for the response
        def _fetch_fact_status():
            with api_state.engine._get_conn() as conn:
                row = conn.execute("SELECT confidence FROM facts WHERE id = ?", (fact_id,)).fetchone()
                return row[0] if row else "unknown"
        
        confidence = await run_in_threadpool(_fetch_fact_status)
        
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
) -> VoteResponse:
    """Cast a reputation-weighted consensus vote (RWC)."""
    try:
        # Ownership check
        def _check_owner():
            with api_state.engine._get_conn() as conn:
                row = conn.execute("SELECT project FROM facts WHERE id = ?", (fact_id,)).fetchone()
                return row[0] if row else None

        project = await run_in_threadpool(_check_owner)
        if not project:
            raise HTTPException(status_code=404, detail=f"Fact #{fact_id} not found")
        if project != auth.tenant_id:
            raise HTTPException(status_code=403, detail="Forbidden: Fact belongs to another tenant")

        # Cast RWC vote
        score = await run_in_threadpool(
            api_state.engine.vote, 
            fact_id=fact_id, 
            agent=auth.key_name or "api_agent", 
            value=req.vote, 
            agent_id=req.agent_id
        )

        # Get updated confidence for the response
        def _fetch_fact_status():
            with api_state.engine._get_conn() as conn:
                row = conn.execute("SELECT confidence FROM facts WHERE id = ?", (fact_id,)).fetchone()
                return row[0] if row else "unknown"

        confidence = await run_in_threadpool(_fetch_fact_status)

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
) -> List[dict]:
    """Retrieve all votes for a specific fact (Tenant Isolated)."""
    # Ownership check
    def _check_owner():
        with api_state.engine._get_conn() as conn:
            row = conn.execute("SELECT project FROM facts WHERE id = ?", (fact_id,)).fetchone()
            return row[0] if row else None

    project = await run_in_threadpool(_check_owner)
    if not project:
        raise HTTPException(status_code=404, detail=f"Fact #{fact_id} not found")
    if project != auth.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    def _get_votes():
        with api_state.engine._get_conn() as conn:
            # Combined query for legacy and v2 votes
            v2_votes = conn.execute(
                """
                SELECT 'v2' as type, v.vote, v.agent_id as agent, v.created_at, a.reputation_score
                FROM consensus_votes_v2 v
                JOIN agents a ON v.agent_id = a.id
                WHERE v.fact_id = ?
                """,
                (fact_id,)
            ).fetchall()
            
            legacy_votes = conn.execute(
                """
                SELECT 'legacy' as type, vote, agent, timestamp as created_at, 0.0 as reputation_score
                FROM consensus_votes
                WHERE fact_id = ?
                """,
                (fact_id,)
            ).fetchall()
            
            return [
                {
                    "type": r[0],
                    "vote": r[1],
                    "agent": r[2],
                    "timestamp": r[3],
                    "reputation": r[4]
                }
                for r in (v2_votes + legacy_votes)
            ]

    votes = await run_in_threadpool(_get_votes)
    return votes



@router.delete("/v1/facts/{fact_id}")
async def deprecate_fact(
    fact_id: int,
    auth: AuthResult = Depends(require_permission("write")),
) -> dict:
    """Soft-deprecate a fact (mark as invalid)."""
    # Ownership check
    def _check_owner():
        with api_state.engine._get_conn() as conn:
            row = conn.execute("SELECT project FROM facts WHERE id = ?", (fact_id,)).fetchone()
            return row[0] if row else None
    
    project = await run_in_threadpool(_check_owner)
    if not project:
        raise HTTPException(status_code=404, detail=f"Fact #{fact_id} not found")
    if project != auth.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    success = await run_in_threadpool(api_state.engine.deprecate, fact_id, project)
    if not success:
        raise HTTPException(status_code=500, detail="Deprecation failed")
    
    return {"message": f"Fact #{fact_id} deprecated", "success": True}

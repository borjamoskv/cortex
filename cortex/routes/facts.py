"""
CORTEX v4.0 - Facts Router.
"""

import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from cortex.api_deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine_async import AsyncCortexEngine
from cortex.i18n import get_trans
from cortex.models import (
    FactResponse,
    StoreRequest,
    StoreResponse,
    VoteRequest,
    VoteResponse,
    VoteV2Request,
)

router = APIRouter(tags=["facts"])
logger = logging.getLogger("uvicorn.error")


@router.post("/v1/facts", response_model=StoreResponse)
async def store_fact(
    req: StoreRequest,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> StoreResponse:
    """Store a fact (scoped to authenticated tenant)."""
    fact_id = await engine.store(
        project=auth.tenant_id,
        content=req.content,
        fact_type=req.fact_type,
        tags=req.tags,
        source=req.source,
        meta=req.meta,
    )
    return StoreResponse(fact_id=fact_id, project=auth.tenant_id, message="Fact stored")


@router.get("/v1/projects/{project}/facts", response_model=list[FactResponse])
async def recall_facts(
    project: str,
    request: Request,
    limit: int | None = Query(None, ge=1, le=1000),
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[FactResponse]:
    """Recall facts for a specific project with tenant isolation."""
    lang = request.headers.get("Accept-Language", "en")
    if project != auth.tenant_id:
        raise HTTPException(status_code=403, detail=get_trans("error_namespace_mismatch", lang))

    facts = await engine.recall(project=project, limit=limit)

    return [
        FactResponse(
            id=f["id"],
            project=f["project"],
            content=f["content"],
            fact_type=f["fact_type"],
            tags=f["tags"],
            confidence=f["confidence"],
            valid_from=f["valid_from"],
            valid_until=f["valid_until"],
            source=f["source"],
            meta=f["meta"],
            created_at=f["created_at"],
            updated_at=f["updated_at"],
            tx_id=f["tx_id"],
            hash=f["hash"],
            consensus_score=f.get("consensus_score", 1.0),
        )
        for f in facts
    ]


@router.post("/v1/facts/{fact_id}/vote", response_model=VoteResponse)
async def cast_vote(
    fact_id: int,
    req: VoteRequest,
    request: Request,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> VoteResponse:
    """Cast a consensus vote (verify/dispute) on a fact."""
    lang = request.headers.get("Accept-Language", "en")
    try:
        fact = await engine.get_fact(fact_id)
        if not fact:
            raise HTTPException(status_code=404, detail=get_trans("error_fact_not_found", lang).format(id=fact_id))

        if fact["project"] != auth.tenant_id:
            raise HTTPException(status_code=403, detail=get_trans("error_forbidden", lang))

        agent_id = auth.key_name or "api_agent"
        score = await engine.vote(fact_id, agent_id, req.value)

        # Confidence is updated automatically by manager
        updated_fact = await engine.get_fact(fact_id)

        return VoteResponse(
            fact_id=fact_id,
            agent=agent_id,
            vote=req.value,
            new_consensus_score=score,
            confidence=updated_fact["confidence"] if updated_fact else "unknown",
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except (sqlite3.Error, OSError, RuntimeError):
        logger.exception("Unexpected error during voting for fact #%d", fact_id)
        raise HTTPException(status_code=500, detail=get_trans("error_internal_server", lang)) from None


@router.post("/v1/facts/{fact_id}/vote-v2", response_model=VoteResponse)
async def cast_vote_v2(
    fact_id: int,
    req: VoteV2Request,
    request: Request,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> VoteResponse:
    """Cast a reputation-weighted consensus vote (RWC)."""
    lang = request.headers.get("Accept-Language", "en")
    try:
        fact = await engine.get_fact(fact_id)
        if not fact:
            raise HTTPException(status_code=404, detail=get_trans("error_fact_not_found", lang).format(id=fact_id))

        if fact["project"] != auth.tenant_id:
            raise HTTPException(status_code=403, detail=get_trans("error_forbidden", lang))

        score = await engine.vote(
            fact_id=fact_id,
            agent=req.agent_id,
            value=req.vote,
        )

        # Re-fetch for updated confidence
        updated_fact = await engine.get_fact(fact_id)

        return VoteResponse(
            fact_id=fact_id,
            agent=req.agent_id,
            vote=req.vote,
            new_consensus_score=score,
            confidence=updated_fact["confidence"] if updated_fact else "unknown",
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except (sqlite3.Error, OSError, RuntimeError):
        logger.exception("RWC Vote failed")
        raise HTTPException(status_code=500, detail=get_trans("error_internal_voting", lang)) from None


@router.get("/v1/facts/{fact_id}/votes", response_model=list[dict])
async def list_votes(
    fact_id: int,
    request: Request,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[dict]:
    """Retrieve all votes for a specific fact (Tenant Isolated)."""
    lang = request.headers.get("Accept-Language", "en")
    fact = await engine.get_fact(fact_id)
    if not fact:
        raise HTTPException(status_code=404, detail=get_trans("error_fact_not_found", lang).format(id=fact_id))

    if fact["project"] != auth.tenant_id:
        raise HTTPException(status_code=403, detail=get_trans("error_forbidden", lang))

    votes = await engine.get_votes(fact_id)

    return [{"agent": v[0], "vote": v[1], "tx_id": v[2]} for v in votes]


@router.delete("/v1/facts/{fact_id}", response_model=dict)
async def deprecate_fact(
    fact_id: int,
    request: Request,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> dict:
    """Soft-deprecate a fact (mark as invalid)."""
    lang = request.headers.get("Accept-Language", "en")
    fact = await engine.get_fact(fact_id)
    if not fact:
        raise HTTPException(status_code=404, detail=get_trans("error_fact_not_found", lang).format(id=fact_id))

    if fact["project"] != auth.tenant_id:
        raise HTTPException(status_code=403, detail=get_trans("error_forbidden", lang))

    success = await engine.deprecate(fact_id, auth.tenant_id)
    if not success:
        raise HTTPException(status_code=500, detail=get_trans("error_deprecation_failed", lang))

    return {"message": f"Fact #{fact_id} deprecated", "success": True}

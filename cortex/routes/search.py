"""
CORTEX v4.0 - Search Router.
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, Query

from cortex.api_deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine_async import AsyncCortexEngine
from cortex.models import SearchRequest, SearchResult

router = APIRouter(tags=["search"])


@router.post("/v1/search", response_model=List[SearchResult])
async def search_facts(
    req: SearchRequest,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> List[SearchResult]:
    """Semantic search across facts (scoped to tenant)."""
    results = await engine.search(
        query=req.query,
        top_k=req.k,
        project=auth.tenant_id,
        as_of=req.as_of,
    )
    return [
        SearchResult(
            fact_id=r.fact_id,
            project=r.project,
            content=r.content,
            fact_type=r.fact_type,
            score=r.score,
            tags=r.tags,
            created_at=r.created_at,
            updated_at=r.updated_at,
            tx_id=r.tx_id,
            hash=r.hash,
        )
        for r in results
    ]


@router.get("/v1/search", response_model=List[SearchResult])
async def search_facts_get(
    query: str = Query(..., max_length=1024),
    k: int = Query(5, ge=1, le=50),
    as_of: Optional[str] = None,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> List[SearchResult]:
    """Semantic search via GET (scoped to tenant)."""
    results = await engine.search(
        query=query,
        top_k=k,
        project=auth.tenant_id,
        as_of=as_of,
    )
    return [
        SearchResult(
            fact_id=r.fact_id,
            project=r.project,
            content=r.content,
            fact_type=r.fact_type,
            score=r.score,
            tags=r.tags,
            created_at=r.created_at,
            updated_at=r.updated_at,
            tx_id=r.tx_id,
            hash=r.hash,
        )
        for r in results
    ]

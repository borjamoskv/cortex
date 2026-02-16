"""
CORTEX v4.0 - Search Router.
"""

from fastapi import APIRouter, Depends, Query
from cortex.auth import AuthResult, require_permission
from cortex.models import SearchRequest, SearchResult
from cortex.api_deps import get_engine
from cortex.engine import CortexEngine

router = APIRouter(tags=["search"])

@router.post("/v1/search", response_model=list[SearchResult])
async def search_facts(
    req: SearchRequest,
    auth: AuthResult = Depends(require_permission("read")),
    engine: CortexEngine = Depends(get_engine),
) -> list[SearchResult]:
    """Semantic search across all facts."""
    results = await engine.search(
        req.query,
        top_k=req.k,
        project=req.project,
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

@router.get("/v1/search", response_model=list[SearchResult])
async def search_facts_get(
    query: str = Query(..., description="Natural language search query"),
    limit: int = Query(5, ge=1, le=50),
    project: str | None = Query(None),
    as_of: str | None = Query(None),
    auth: AuthResult = Depends(require_permission("read")),
    engine: CortexEngine = Depends(get_engine),
) -> list[SearchResult]:
    """Semantic search (GET) for frontend convenience."""
    results = await engine.search(
        query,
        top_k=limit,
        project=project,
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

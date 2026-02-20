# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v4.2 — Ask Router (RAG endpoint).

POST /v1/ask — Search facts → synthesize with LLM → return answer.
Gracefully returns 503 if no LLM provider is configured.
"""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from cortex.api_deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine_async import AsyncCortexEngine
from cortex.llm.manager import LLMManager
from cortex.llm.provider import LLMProvider

logger = logging.getLogger("cortex.routes.ask")

router = APIRouter(tags=["ask"])

# ─── Singleton LLM Manager ──────────────────────────────────────────
_llm_manager = LLMManager()


# ─── Request / Response Models ───────────────────────────────────────

class AskRequest(BaseModel):
    """RAG query: search CORTEX memory and synthesize an answer."""
    query: str = Field(..., min_length=1, max_length=4096, description="Natural language question")
    project: str | None = Field(None, description="Filter by project (optional)")
    k: int = Field(10, ge=1, le=50, description="Number of facts to retrieve")
    temperature: float = Field(0.3, ge=0.0, le=2.0, description="LLM sampling temperature")
    max_tokens: int = Field(2048, ge=64, le=8192, description="Max response tokens")
    system_prompt: str | None = Field(None, description="Override system prompt (optional)")


class AskSource(BaseModel):
    """A source fact that contributed to the answer."""
    fact_id: int
    content: str
    score: float
    project: str


class AskResponse(BaseModel):
    """RAG response with answer and sources."""
    answer: str
    sources: list[AskSource]
    model: str
    provider: str
    facts_found: int


class LLMStatusResponse(BaseModel):
    """LLM provider status."""
    available: bool
    provider: str
    model: str | None = None
    supported_providers: list[str]


# ─── System Prompt ───────────────────────────────────────────────────

CORTEX_SYSTEM_PROMPT = """You are CORTEX, a Sovereign Memory Engine for Enterprise AI Swarms. 
You are strictly the memory product, NOT the active agent.
You answer questions based EXCLUSIVELY on the facts provided below.
If the facts don't contain enough information, say so clearly. Do not hallucinate.
Be concise, precise, and cite fact IDs when relevant. Maintain an authoritative, industrial tone.
Respond in the same language as the user's question."""


# ─── Endpoints ───────────────────────────────────────────────────────

@router.post("/v1/ask", response_model=AskResponse)
async def ask_cortex(
    req: AskRequest,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
):
    """RAG endpoint: search → synthesize → answer.

    Searches CORTEX memory for relevant facts, then uses the configured
    LLM to synthesize an answer grounded in those facts.

    Returns 503 if no LLM provider is configured.
    """
    if not _llm_manager.available:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "No LLM provider configured. "
                "Set CORTEX_LLM_PROVIDER env variable. "
                f"Supported: {LLMProvider.list_providers()}",
            },
        )

    # 1. Search CORTEX memory
    results = await engine.search(
        query=req.query,
        top_k=req.k,
        project=auth.tenant_id or req.project,
    )

    # 2. Build context from retrieved facts
    if results:
        context_lines = []
        for i, r in enumerate(results, 1):
            context_lines.append(
                f"[Fact #{r.fact_id}] (project: {r.project}, score: {r.score:.3f})\n{r.content}"
            )
        context = "\n\n".join(context_lines)
    else:
        context = "(No facts found matching the query.)"

    # 3. Construct prompt
    system = req.system_prompt or CORTEX_SYSTEM_PROMPT
    prompt = f"""## Retrieved Facts from CORTEX Memory

{context}

## Question

{req.query}

## Instructions

Answer the question above using ONLY the facts provided. Cite [Fact #ID] when referencing specific facts."""

    # 4. Call LLM
    try:
        answer = await _llm_manager.complete(
            prompt=prompt,
            system=system,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
    except (ConnectionError, OSError, RuntimeError) as e:
        logger.error("LLM completion failed: %s", e)
        return JSONResponse(
            status_code=502,
            content={"detail": f"LLM provider error: {str(e)}"},
        )

    if answer is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "LLM provider returned no response."},
        )

    # 5. Build response
    sources = [
        AskSource(
            fact_id=r.fact_id,
            content=r.content[:200],  # Truncate for response size
            score=r.score,
            project=r.project,
        )
        for r in results
    ]

    provider = _llm_manager.provider
    return AskResponse(
        answer=answer,
        sources=sources,
        model=provider.model if provider else "unknown",
        provider=provider.provider_name if provider else "unknown",
        facts_found=len(results),
    )


@router.get("/v1/llm/status", response_model=LLMStatusResponse)
async def llm_status(
    auth: AuthResult = Depends(require_permission("read")),
):
    """Check LLM provider status and list supported providers."""
    provider = _llm_manager.provider
    return LLMStatusResponse(
        available=_llm_manager.available,
        provider=_llm_manager.provider_name or "none",
        model=provider.model if provider else None,
        supported_providers=LLMProvider.list_providers(),
    )

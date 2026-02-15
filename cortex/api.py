"""
CORTEX v4.0 — REST API.

FastAPI server exposing the sovereign memory engine.
Authenticated via API keys with tenant isolation.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from cortex.auth import AuthManager, AuthResult
from cortex.engine import CortexEngine
from cortex.timing import TimingTracker

# ─── Config ───────────────────────────────────────────────────────────

DB_PATH = os.environ.get("CORTEX_DB", os.path.expanduser("~/.cortex/cortex.db"))

# ─── Globals (initialized at startup) ────────────────────────────────

engine: CortexEngine | None = None
auth_manager: AuthManager | None = None
tracker: TimingTracker | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize engine, auth, and timing on startup."""
    global engine, auth_manager, tracker
    engine = CortexEngine(DB_PATH)
    engine.init_db()
    auth_manager = AuthManager(DB_PATH)
    # Timing tracker shares the engine's connection
    tracker = TimingTracker(engine._get_conn())
    yield


app = FastAPI(
    title="CORTEX — Sovereign Memory API",
    description="Local-first memory infrastructure for AI agents. "
    "Vector search, temporal facts, cryptographic ledger.",
    version="4.0.0a1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Auth Dependency ──────────────────────────────────────────────────


async def require_auth(
    authorization: str = Header(None, description="Bearer <api-key>"),
) -> AuthResult:
    """Extract and validate API key from Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Use: Bearer <api-key>")

    result = auth_manager.authenticate(parts[1])
    if not result.authenticated:
        raise HTTPException(status_code=401, detail=result.error)
    return result


def require_permission(permission: str):
    """Factory for permission-checking dependencies."""

    async def checker(auth: AuthResult = Depends(require_auth)) -> AuthResult:
        if permission not in auth.permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Missing permission: {permission}",
            )
        return auth

    return checker


# ─── Request/Response Models ──────────────────────────────────────────


class StoreRequest(BaseModel):
    project: str = Field(..., description="Project/namespace for the fact")
    content: str = Field(..., description="The fact content")
    fact_type: str = Field("knowledge", description="Type: knowledge, decision, mistake, bridge, ghost")
    tags: list[str] = Field(default_factory=list, description="Optional tags")
    metadata: dict | None = Field(None, description="Optional JSON metadata")


class StoreResponse(BaseModel):
    fact_id: int
    project: str
    message: str


class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language search query")
    k: int = Field(5, ge=1, le=50, description="Number of results")
    project: str | None = Field(None, description="Filter by project")


class SearchResult(BaseModel):
    fact_id: int
    project: str
    content: str
    fact_type: str
    score: float
    tags: list[str]


class FactResponse(BaseModel):
    id: int
    project: str
    content: str
    fact_type: str
    tags: list[str]
    created_at: str
    valid_from: str
    valid_until: str | None
    metadata: dict | None


class StatusResponse(BaseModel):
    version: str
    total_facts: int
    active_facts: int
    deprecated: int
    projects: int
    embeddings: int
    transactions: int
    db_size_mb: float


class HeartbeatRequest(BaseModel):
    project: str
    entity: str = ""
    category: Optional[str] = None
    branch: Optional[str] = None
    language: Optional[str] = None
    meta: Optional[dict] = None


class TimeSummaryResponse(BaseModel):
    total_seconds: int
    total_hours: float
    by_category: dict[str, int]
    by_project: dict[str, int]
    entries: int
    heartbeats: int
    top_entities: list[list]  # [[entity, count], ...]


# ─── Endpoints ────────────────────────────────────────────────────────


@app.get("/", tags=["health"])
async def root():
    return {"service": "cortex", "version": "4.0.0a1", "status": "operational"}


@app.get("/health", tags=["health"])
async def health():
    try:
        stats = engine.stats()
        return {"status": "healthy", "facts": stats["total_facts"], "version": "4.0.0a1"}
    except (sqlite3.OperationalError, KeyError):
        return {"status": "healthy", "facts": 0, "version": "4.0.0a1"}


@app.post("/v1/facts", response_model=StoreResponse, tags=["facts"])
async def store_fact(
    req: StoreRequest,
    auth: AuthResult = Depends(require_permission("write")),
):
    """Store a new fact with vector embedding."""
    fact_id = engine.store(
        project=req.project,
        content=req.content,
        fact_type=req.fact_type,
        tags=req.tags,
        meta=req.metadata,
        source=f"api:{auth.key_name}",
    )
    return StoreResponse(
        fact_id=fact_id,
        project=req.project,
        message=f"Stored fact #{fact_id}",
    )


@app.post("/v1/search", response_model=list[SearchResult], tags=["search"])
async def search_facts(
    req: SearchRequest,
    auth: AuthResult = Depends(require_permission("read")),
):
    """Semantic search across all facts."""
    results = engine.search(req.query, top_k=req.k)
    return [
        SearchResult(
            fact_id=r.fact_id,
            project=r.project,
            content=r.content,
            fact_type=r.fact_type,
            score=r.score,
            tags=r.tags,
        )
        for r in results
    ]


@app.get("/v1/projects/{project}/facts", response_model=list[FactResponse], tags=["facts"])
async def recall_project(
    project: str,
    include_deprecated: bool = Query(False),
    auth: AuthResult = Depends(require_permission("read")),
):
    """Recall all facts for a project."""
    if include_deprecated:
        facts = engine.history(project)
    else:
        facts = engine.recall(project)

    return [
        FactResponse(
            id=f.id,
            project=f.project,
            content=f.content,
            fact_type=f.fact_type,
            tags=f.tags,
            created_at=f.valid_from,
            valid_from=f.valid_from,
            valid_until=f.valid_until,
            metadata=f.meta if f.meta else None,
        )
        for f in facts
    ]


@app.delete("/v1/facts/{fact_id}", tags=["facts"])
async def deprecate_fact(
    fact_id: int,
    auth: AuthResult = Depends(require_permission("write")),
):
    """Deprecate a fact (soft delete — never removes data)."""
    success = engine.deprecate(fact_id, reason=f"api:{auth.key_name}")
    if not success:
        raise HTTPException(status_code=404, detail=f"Fact #{fact_id} not found or already deprecated")
    return {"message": f"Fact #{fact_id} deprecated", "fact_id": fact_id}


@app.get("/v1/status", response_model=StatusResponse, tags=["admin"])
async def status(auth: AuthResult = Depends(require_permission("read"))):
    """Get engine status and statistics."""
    stats = engine.stats()
    return StatusResponse(
        version="4.0.0a1",
        total_facts=stats["total_facts"],
        active_facts=stats["active_facts"],
        deprecated=stats["deprecated_facts"],
        projects=stats["project_count"],
        embeddings=stats["embeddings"],
        transactions=stats["transactions"],
        db_size_mb=stats["db_size_mb"],
    )


# ─── Time Tracking Endpoints ────────────────────────────────────────


@app.post("/v1/heartbeat", tags=["timing"])
async def record_heartbeat(
    req: HeartbeatRequest,
    auth: AuthResult = Depends(require_permission("write")),
):
    """Record an activity heartbeat for automatic time tracking."""
    hb_id = tracker.heartbeat(
        project=req.project,
        entity=req.entity,
        category=req.category,
        branch=req.branch,
        language=req.language,
        meta=req.meta,
    )
    # Auto-flush after every heartbeat to keep entries fresh
    tracker.flush()
    return {"id": hb_id, "status": "recorded"}


@app.get("/v1/time/today", tags=["timing"])
async def time_today(
    project: Optional[str] = Query(None),
    auth: AuthResult = Depends(require_permission("read")),
):
    """Get today's time tracking summary."""
    summary = tracker.today(project=project)
    return TimeSummaryResponse(
        total_seconds=summary.total_seconds,
        total_hours=summary.total_hours,
        by_category=summary.by_category,
        by_project=summary.by_project,
        entries=summary.entries,
        heartbeats=summary.heartbeats,
        top_entities=[[e, c] for e, c in summary.top_entities],
    )


@app.get("/v1/time", tags=["timing"])
async def time_report(
    project: Optional[str] = Query(None),
    days: int = Query(7),
    auth: AuthResult = Depends(require_permission("read")),
):
    """Get time tracking report for the last N days."""
    summary = tracker.report(project=project, days=days)
    return TimeSummaryResponse(
        total_seconds=summary.total_seconds,
        total_hours=summary.total_hours,
        by_category=summary.by_category,
        by_project=summary.by_project,
        entries=summary.entries,
        heartbeats=summary.heartbeats,
        top_entities=[[e, c] for e, c in summary.top_entities],
    )


@app.get("/v1/time/history", tags=["timing"])
async def get_time_history(
    days: int = Query(7, ge=1, le=365),
    auth: AuthResult = Depends(require_permission("read")),
):
    """Get daily time history."""
    return tracker.daily(days=days)


# ─── Admin Endpoints ─────────────────────────────────────────────────


@app.post("/v1/admin/keys", tags=["admin"])
async def create_api_key(
    name: str = Query(...),
    tenant_id: str = Query("default"),
    authorization: str = Header(None),
):
    """Create a new API key. First key requires no auth (bootstrap)."""
    keys = auth_manager.list_keys()
    if keys:
        # Require auth after first key
        if not authorization:
            raise HTTPException(status_code=401, detail="Auth required")
        parts = authorization.split(" ", 1)
        if len(parts) != 2:
            raise HTTPException(status_code=401, detail="Invalid auth")
        result = auth_manager.authenticate(parts[1])
        if not result.authenticated:
            raise HTTPException(status_code=401, detail=result.error)
        if "admin" not in result.permissions:
            raise HTTPException(status_code=403, detail="Admin permission required")

    raw_key, api_key = auth_manager.create_key(
        name=name,
        tenant_id=tenant_id,
        permissions=["read", "write", "admin"],
    )
    return {
        "key": raw_key,
        "name": api_key.name,
        "prefix": api_key.key_prefix,
        "tenant_id": api_key.tenant_id,
        "message": "⚠️  Save this key — it will NOT be shown again.",
    }


@app.get("/v1/admin/keys", tags=["admin"])
async def list_api_keys(auth: AuthResult = Depends(require_permission("admin"))):
    """List all API keys (hashed, never reveals raw key)."""
    keys = auth_manager.list_keys()
    return [
        {
            "id": k.id,
            "name": k.name,
            "prefix": k.key_prefix,
            "tenant_id": k.tenant_id,
            "permissions": k.permissions,
            "is_active": k.is_active,
            "created_at": k.created_at,
            "last_used": k.last_used,
        }
        for k in keys
    ]


# ─── Daemon Status ────────────────────────────────────────────────────


@app.get("/v1/daemon/status", tags=["daemon"])
async def daemon_status(auth: AuthResult = Depends(require_permission("read"))):
    """Get last daemon watchdog check results."""
    from cortex.daemon import MoskvDaemon
    status = MoskvDaemon.load_status()
    if not status:
        return {"status": "no_data", "message": "Daemon has not run yet."}
    return status


# ─── Dashboard ───────────────────────────────────────────────────────


@app.get("/dashboard", response_class=HTMLResponse, tags=["dashboard"])
async def dashboard():
    """Serve the embedded memory dashboard."""
    from cortex.dashboard import get_dashboard_html
    return get_dashboard_html()

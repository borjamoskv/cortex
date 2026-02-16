"""
CORTEX v4.0 — REST API.

FastAPI server exposing the sovereign memory engine.
Main entry point for initialization and routing.
"""

from __future__ import annotations

import logging
import random
import sqlite3
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from cortex.auth import AuthManager, AuthResult, get_auth_manager, require_auth, require_permission
from cortex.engine import CortexEngine
from cortex.timing import TimingTracker
from cortex.config import DB_PATH, ALLOWED_ORIGINS, RATE_LIMIT, RATE_WINDOW
from cortex.hive import router as hive_router
from cortex.metrics import MetricsMiddleware, metrics
from cortex import api_state

# Import routers
from cortex.routes import (
    facts as facts_router,
    search as search_router,
    admin as admin_router,
    timing as timing_router,
    daemon as daemon_router,
    dashboard as dashboard_router,
    agents as agents_router,
    graph as graph_router,
    ledger as ledger_router,
    missions as missions_router,
    mejoralo as mejoralo_router,
)

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize engine, auth, and timing on startup."""
    engine = CortexEngine(DB_PATH)
    engine.init_db()
    auth_manager = AuthManager(DB_PATH)
    
    # Sync to cortex.auth so dependencies use the same instance
    import cortex.auth
    cortex.auth._auth_manager = auth_manager
    
    # Timing tracker gets its own connection to avoid SQLite locking issues
    timing_conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    tracker = TimingTracker(timing_conn)
    
    # Store in app state to avoid globals
    app.state.engine = engine
    app.state.auth_manager = auth_manager
    app.state.tracker = tracker
    
    # Backward compatibility for api_state (temporary)
    api_state.engine = engine
    api_state.auth_manager = auth_manager
    api_state.tracker = tracker
    
    try:
        yield
    finally:
        engine.close()
        timing_conn.close()
        cortex.auth._auth_manager = None
        api_state.engine = None
        api_state.auth_manager = None
        api_state.tracker = None


app = FastAPI(
    title="CORTEX — Sovereign Memory API",
    description="Local-first memory infrastructure for AI agents. "
    "Vector search, temporal facts, cryptographic ledger.",
    version="4.0.0a1",
    lifespan=lifespan,
)


# ─── Middleware ──────────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory rate limiter (Sliding Window)."""
    
    def __init__(self, app, limit: int = 100, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.requests: dict[str, list[float]] = {}
        
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Remove timestamps older than window
        self.requests[client_ip] = [t for t in self.requests[client_ip] if now - t < self.window]
        
        if len(self.requests[client_ip]) >= self.limit:
            logger.warning("Rate limit exceeded for %s", client_ip)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too Many Requests. Please slow down."},
                headers={"Retry-After": str(self.window)}
            )
            
        self.requests[client_ip].append(now)
        
        # Periodic cleanup (1% of requests)
        if random.random() < 0.01:
            expired_keys = [ip for ip, reqs in self.requests.items() if not reqs or now - reqs[-1] > self.window]
            for ip in expired_keys:
                del self.requests[ip]
        
        return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(RateLimitMiddleware, limit=RATE_LIMIT, window=RATE_WINDOW)
app.add_middleware(MetricsMiddleware)


# ─── Dependencies ───────────────────────────────────────────────────

from cortex.api_deps import get_engine, get_tracker

# ─── Exception Handlers ──────────────────────────────────────────────

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})

@app.exception_handler(sqlite3.Error)
async def sqlite_error_handler(request: Request, exc: sqlite3.Error) -> JSONResponse:
    logger.error("Database error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal database error"})

@app.exception_handler(Exception)
async def universal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred."}
    )


# ─── Routes ──────────────────────────────────────────────────────────

@app.get("/", tags=["health"])
async def root_node() -> dict:
    return {"service": "cortex", "version": "4.0.0a1", "status": "operational"}

@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Simple status check for load balancers."""
    return {"status": "healthy", "engine": "online", "version": "4.0.0a1"}

@app.get("/metrics", tags=["health"])
async def get_metrics():
    """Expose Prometheus metrics."""
    from fastapi.responses import Response
    return Response(content=metrics.to_prometheus(), media_type="text/plain")

# Include logical routers
app.include_router(facts_router.router)
app.include_router(search_router.router)
app.include_router(admin_router.router)
app.include_router(timing_router.router)
app.include_router(daemon_router.router)
app.include_router(dashboard_router.router)
app.include_router(agents_router.router)
app.include_router(graph_router.router)
app.include_router(ledger_router.router)
app.include_router(missions_router.router)
app.include_router(mejoralo_router.router)
app.include_router(hive_router)

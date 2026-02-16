"""
CORTEX v4.0 — REST API.

FastAPI server exposing the sovereign memory engine.
Main entry point for initialization and routing.
"""

import logging
import sqlite3
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from cortex import api_state
from cortex.auth import AuthManager
from cortex.config import ALLOWED_ORIGINS, DB_PATH, RATE_LIMIT, RATE_WINDOW
from cortex.engine import CortexEngine
from cortex.hive import router as hive_router
from cortex.metrics import MetricsMiddleware, metrics
from cortex.routes import (
    admin as admin_router,
)
from cortex.routes import (
    agents as agents_router,
)
from cortex.routes import (
    daemon as daemon_router,
)
from cortex.routes import (
    dashboard as dashboard_router,
)

# Import routers
from cortex.routes import (
    facts as facts_router,
)
from cortex.routes import (
    gate as gate_router,
)
from cortex.routes import (
    graph as graph_router,
)
from cortex.routes import (
    ledger as ledger_router,
)
from cortex.routes import (
    mejoralo as mejoralo_router,
)
from cortex.routes import (
    missions as missions_router,
)
from cortex.routes import (
    search as search_router,
)
from cortex.routes import (
    timing as timing_router,
)
from cortex.timing import TimingTracker

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize async connection pool, engine, auth, and timing on startup."""
    from cortex.connection_pool import CortexConnectionPool
    from cortex.engine_async import AsyncCortexEngine

    # 1. Initialize Core Async Foundation (Wave 5)
    pool = CortexConnectionPool(DB_PATH)
    await pool.initialize()
    async_engine = AsyncCortexEngine(pool, DB_PATH)

    # 2. Legacy Engine for compatibility
    engine = CortexEngine(DB_PATH)
    await engine.init_db()
    auth_manager = AuthManager(DB_PATH)

    # Sync to cortex.auth so dependencies use the same instance
    import cortex.auth

    cortex.auth._auth_manager = auth_manager

    # Timing tracker gets its own connection to avoid SQLite locking issues
    timing_conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    tracker = TimingTracker(timing_conn)

    # Store in app state
    app.state.pool = pool
    app.state.async_engine = async_engine
    app.state.engine = engine  # Kept as 'engine' for legacy routes
    app.state.auth_manager = auth_manager
    app.state.tracker = tracker

    # Backward compatibility for api_state
    api_state.engine = engine
    api_state.auth_manager = auth_manager
    api_state.tracker = tracker

    try:
        yield
    finally:
        await pool.close()
        await engine.close()
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
    """In-memory rate limiter (Sliding Window, bounded).

    Tracks at most ``MAX_TRACKED_IPS`` unique clients.  When the limit
    is reached, the oldest 20 % of entries are evicted to keep memory
    usage predictable under DDoS or scanner traffic.
    """

    MAX_TRACKED_IPS = 10_000

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
                headers={"Retry-After": str(self.window)},
            )

        self.requests[client_ip].append(now)

        # Bounded eviction — deterministic, not probabilistic
        if len(self.requests) > self.MAX_TRACKED_IPS:
            self._evict(now)

        return await call_next(request)

    def _evict(self, now: float) -> None:
        """Remove stale entries; if still over limit, drop oldest 20 %."""
        # First pass: remove truly expired IPs
        expired = [ip for ip, ts in self.requests.items() if not ts or now - ts[-1] > self.window]
        for ip in expired:
            del self.requests[ip]

        # Second pass: if still over limit, drop oldest 20 %
        if len(self.requests) > self.MAX_TRACKED_IPS:
            by_age = sorted(
                self.requests.items(),
                key=lambda kv: kv[1][-1] if kv[1] else 0,
            )
            to_drop = max(1, len(by_age) // 5)
            for ip, _ in by_age[:to_drop]:
                del self.requests[ip]


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(RateLimitMiddleware, limit=RATE_LIMIT, window=RATE_WINDOW)
app.add_middleware(MetricsMiddleware)


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
    return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred."})


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
app.include_router(gate_router.router)
app.include_router(hive_router)

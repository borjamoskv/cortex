"""
CORTEX v4.0 — API Dependencies.
Shared dependencies for FastAPI routes.
"""

from __future__ import annotations

from fastapi import Request

from cortex.engine import CortexEngine
from cortex.engine_async import AsyncCortexEngine
from cortex.timing import TimingTracker


def get_engine(request: Request) -> CortexEngine:
    """Inject the legacy sync-wrapped engine from app state."""
    return request.app.state.engine

def get_async_engine(request: Request) -> AsyncCortexEngine:
    """Inject the native async engine (Wave 5)."""
    return request.app.state.async_engine

def get_tracker(request: Request) -> TimingTracker:
    """Inject the timing tracker from app state."""
    return request.app.state.tracker

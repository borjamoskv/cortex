"""
CORTEX MCP Server v2 — Optimized Multi-Transport Implementation.
Sovereign memory infrastructure for AI agents.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import sqlite3
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("cortex.mcp.v2")

# ─── Server Setup ─────────────────────────────────────────────────────

_MCP_AVAILABLE = False
try:
    from mcp.server.fastmcp import FastMCP
    _MCP_AVAILABLE = True
except ImportError:
    FastMCP = None  # type: ignore
    logger.debug("MCP SDK not installed. Install with: pip install 'cortex-memory[mcp]'")


@dataclass
class MCPServerConfig:
    """Configuration for MCP server."""
    db_path: str = "~/.cortex/cortex.db"
    max_workers: int = 4
    query_cache_size: int = 1000
    enable_metrics: bool = True
    transport: str = "stdio"  # "stdio", "sse"
    host: str = "127.0.0.1"
    port: int = 9999


class MCPMetrics:
    """Runtime metrics for the MCP server."""
    def __init__(self):
        self.requests_total = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.errors_total = 0
        self.start_at = datetime.now().isoformat()

    def record_request(self, cached: bool = False):
        self.requests_total += 1
        if cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def record_error(self):
        self.errors_total += 1

    def get_summary(self) -> dict:
        return {
            "requests_total": self.requests_total,
            "cache_hit_rate": self.cache_hits / max(1, (self.cache_hits + self.cache_misses)),
            "errors_total": self.errors_total,
            "uptime_since": self.start_at
        }


class SimpleAsyncCache:
    """A minimal TTL-aware cache for semantic search results."""
    def __init__(self, maxsize: int = 100, ttl_seconds: int = 300):
        self.maxsize = maxsize
        self.ttl = ttl_seconds
        self._cache: Dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        timestamp, value = self._cache[key]
        if time.time() - timestamp > self.ttl:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: Any):
        if len(self._cache) >= self.maxsize:
            # Simple eviction
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[key] = (time.time(), value)

    def clear(self):
        self._cache.clear()


class AsyncConnectionPool:
    """Async-aware SQLite connection pool with health checks and timeouts."""
    def __init__(self, db_path: str, max_connections: int = 5, acquire_timeout: float = 5.0):
        self.db_path = os.path.expanduser(db_path)
        self.max_connections = max_connections
        self.acquire_timeout = acquire_timeout
        self._pool: asyncio.Queue[sqlite3.Connection] = asyncio.Queue(maxsize=max_connections)
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> bool:
        """Initialize the pool with validated connections."""
        async with self._lock:
            if self._initialized:
                return True
            
            logger.debug("Initializing connection pool for %s", self.db_path)
            created = 0
            try:
                for _ in range(self.max_connections):
                    conn = sqlite3.connect(
                        self.db_path,
                        check_same_thread=False,
                        timeout=30.0
                    )
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA synchronous=NORMAL")
                    # Quick health check
                    conn.execute("SELECT 1").fetchone()
                    await self._pool.put(conn)
                    created += 1
                self._initialized = True
                return True
            except Exception as e:
                logger.error("Failed to initialize connection pool: %s", e)
                # Cleanup if partially created
                await self.close()
                return False

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[sqlite3.Connection]:
        """Acquire a connection with timeout."""
        try:
            conn = await asyncio.wait_for(self._pool.get(), timeout=self.acquire_timeout)
        except asyncio.TimeoutError:
            logger.error("Connection pool exhausted (timeout after %ss)", self.acquire_timeout)
            raise RuntimeError("Database connection timed out")

        try:
            # Verify connection is still alive
            try:
                conn.execute("SELECT 1")
            except sqlite3.Error:
                logger.warning("Reviving stale database connection")
                conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
                conn.execute("PRAGMA journal_mode=WAL")
            
            yield conn
        finally:
            await self._pool.put(conn)

    async def close(self):
        """Cleanly close all connections in the pool."""
        async with self._lock:
            while not self._pool.empty():
                conn = await self._pool.get()
                try:
                    conn.close()
                except Exception:
                    pass
            self._initialized = False


def create_mcp_server(config: Optional[MCPServerConfig] = None) -> FastMCP:
    """Create and configure an optimized CORTEX MCP server instance."""
    if not _MCP_AVAILABLE:
        raise ImportError("MCP SDK not installed. Install with: pip install 'cortex-memory[mcp]'")

    cfg = config or MCPServerConfig()
    mcp = FastMCP("CORTEX Memory v2")
    
    metrics = MCPMetrics()
    executor = ThreadPoolExecutor(max_workers=cfg.max_workers)
    pool = AsyncConnectionPool(cfg.db_path, max_connections=cfg.max_workers)
    
    # State management inside the function closure
    _state = {"initialized": False}

    async def ensure_initialized():
        if not _state["initialized"]:
            await pool.initialize()
            _state["initialized"] = True

    @lru_cache(maxsize=cfg.query_cache_size)
    def cached_search(query: str, project: Optional[str], top_k: int):
        # This is a sync bridge for lru_cache; actual IO happens in run_in_executor
        pass

    search_cache = SimpleAsyncCache(maxsize=cfg.query_cache_size)

    # ─── Tools ────────────────────────────────────────────────────

    @mcp.tool()
    async def cortex_store(
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: str = "[]",
        source: str = "",
    ) -> str:
        """Store a fact in CORTEX memory."""
        await ensure_initialized()
        from cortex.engine import CortexEngine
        
        try:
            parsed_tags = json.loads(tags) if tags else []
        except json.JSONDecodeError:
            parsed_tags = []

        async with pool.acquire() as conn:
            engine = CortexEngine(cfg.db_path, auto_embed=False)
            engine._conn = conn
            
            loop = asyncio.get_event_loop()
            fact_id = await loop.run_in_executor(
                executor,
                engine.store,
                project,
                content,
                fact_type,
                parsed_tags,
                "stated",
                source or None
            )
            
        metrics.record_request()
        # Invalidate search cache on store
        search_cache.clear()
        return f"✓ Stored fact #{fact_id} in project '{project}'"

    @mcp.tool()
    async def cortex_search(
        query: str,
        project: str = "",
        top_k: int = 5,
    ) -> str:
        """Search CORTEX memory using semantic + text hybrid search."""
        await ensure_initialized()
        
        # Caching logic
        cache_key = f"{query}:{project}:{top_k}"
        cached_result = search_cache.get(cache_key)
        if cached_result:
            metrics.record_request(cached=True)
            return cached_result

        from cortex.engine import CortexEngine
        
        async with pool.acquire() as conn:
            engine = CortexEngine(cfg.db_path, auto_embed=False)
            engine._conn = conn
            
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                executor,
                engine.search,
                query,
                project or None,
                min(max(top_k, 1), 20)
            )

        if not results:
            search_cache.set(cache_key, "No results found.")
            return "No results found."

        metrics.record_request()
        lines = [f"Found {len(results)} results:\n"]
        for r in results:
            lines.append(
                f"[#{r.fact_id}] (score: {r.score:.3f}) "
                f"[{r.project}/{r.fact_type}]\n{r.content}\n"
            )
        
        output = "\n".join(lines)
        search_cache.set(cache_key, output)
        return output

    @mcp.tool()
    async def cortex_status() -> str:
        """Get CORTEX system status and metrics."""
        await ensure_initialized()
        from cortex.engine import CortexEngine
        
        async with pool.acquire() as conn:
            engine = CortexEngine(cfg.db_path, auto_embed=False)
            engine._conn = conn
            stats = engine.stats()
            
        m_summary = metrics.get_summary()
        return (
            f"CORTEX Status (Optimized v2):\n"
            f"  Facts: {stats.get('total_facts', 0)} total, "
            f"{stats.get('active_facts', 0)} active\n"
            f"  Projects: {stats.get('projects', 0)}\n"
            f"  DB Size: {stats.get('db_size_mb', 0):.1f} MB\n"
            f"  MCP Metrics: {json.dumps(m_summary, indent=2)}"
        )

    @mcp.tool()
    async def cortex_ledger_verify() -> str:
        """Perform a full integrity check on the CORTEX ledger."""
        await ensure_initialized()
        from cortex.ledger import ImmutableLedger
        
        async with pool.acquire() as conn:
            ledger = ImmutableLedger(conn)
            report = await asyncio.get_event_loop().run_in_executor(
                executor,
                ledger.verify_integrity
            )
            
        if report["valid"]:
            return (f"✅ Ledger Integrity: OK\n"
                    f"Transactions verified: {report['tx_checked']}\n"
                    f"Facts checked: {report['facts_checked']}")
        else:
            return (f"❌ Ledger Integrity: VIOLATION\n"
                    f"Violations: {json.dumps(report['violations'], indent=2)}")

    return mcp


def run_server(config: Optional[MCPServerConfig] = None) -> None:
    """Start the CORTEX MCP server."""
    mcp = create_mcp_server(config)
    cfg = config or MCPServerConfig()
    
    if cfg.transport == "sse":
        logger.info(f"Starting CORTEX MCP server v2 (SSE) on {cfg.host}:{cfg.port}")
        mcp.run_sse(host=cfg.host, port=cfg.port)
    else:
        logger.info("Starting CORTEX MCP server v2 (stdio)")
        mcp.run_stdio()

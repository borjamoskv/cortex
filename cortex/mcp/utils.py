"""MCP Server Utilities.

Configuration, Metrics, Caching, and Connection Pooling.
"""

import asyncio
import logging
import os
import sqlite3
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator, Dict, Optional

logger = logging.getLogger("cortex.mcp.utils")


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
            "uptime_since": self.start_at,
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
            try:
                for _ in range(self.max_connections):
                    conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA synchronous=NORMAL")
                    # Quick health check
                    conn.execute("SELECT 1").fetchone()
                    await self._pool.put(conn)
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
        conn: Optional[sqlite3.Connection] = None
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
            if conn:
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

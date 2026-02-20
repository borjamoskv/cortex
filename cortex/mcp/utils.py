"""MCP Server Utilities.

Configuration, Metrics, Caching, and Connection Pooling.
"""

import asyncio
import aiosqlite
import logging
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

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
        self._cache: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
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
        self._pool: asyncio.Queue[aiosqlite.Connection] = asyncio.Queue(maxsize=max_connections)
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
                    conn = await aiosqlite.connect(self.db_path, timeout=30.0)
                    await conn.execute("PRAGMA journal_mode=WAL")
                    await conn.execute("PRAGMA synchronous=NORMAL")
                    # Quick health check
                    async with conn.execute("SELECT 1") as cursor:
                        await cursor.fetchone()
                    await self._pool.put(conn)
                self._initialized = True
                return True
            except (OSError, ValueError, KeyError) as e:
                logger.error("Failed to initialize connection pool: %s", e)
                # Cleanup if partially created
                await self.close()
                return False

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[aiosqlite.Connection]:
        """Acquire a connection with timeout."""
        conn: aiosqlite.Connection | None = None
        try:
            conn = await asyncio.wait_for(self._pool.get(), timeout=self.acquire_timeout)
        except asyncio.TimeoutError:
            logger.error("Connection pool exhausted (timeout after %ss)", self.acquire_timeout)
            raise RuntimeError("Database connection timed out") from None

        try:
            # Verify connection is still alive
            try:
                await conn.execute("SELECT 1")
            except (OSError, ValueError, KeyError):
                logger.warning("Reviving stale database connection")
                conn = await aiosqlite.connect(self.db_path, timeout=30.0)
                await conn.execute("PRAGMA journal_mode=WAL")

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
                    await conn.close()
                except (OSError, ValueError, KeyError):
                    pass
            self._initialized = False

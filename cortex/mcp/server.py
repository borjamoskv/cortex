"""MCP Server Implementation.

Core logic for the CORTEX MCP server.
"""
import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from cortex.engine import CortexEngine
from cortex.engine.ledger import ImmutableLedger
from cortex.graph.engine import get_graph_async
from functools import lru_cache
from typing import Optional

from cortex.mcp.utils import (
    MCPServerConfig,
    MCPMetrics,
    SimpleAsyncCache,
    AsyncConnectionPool,
)

logger = logging.getLogger("cortex.mcp.server")

_MCP_AVAILABLE = False
try:
    from mcp.server.fastmcp import FastMCP
    _MCP_AVAILABLE = True
except ImportError:
    FastMCP = None  # type: ignore
    logger.debug("MCP SDK not installed. Install with: pip install 'cortex-memory[mcp]'")


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
        except (json.JSONDecodeError, TypeError):
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
            # Use get_connection() for public API consistency
            _ = engine.get_connection()
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
        from cortex.engine.ledger import ImmutableLedger
        
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

"""MCP Server Implementation.

Core logic for the CORTEX MCP Trust Server.
Provides memory, search, and EU AI Act compliance tools.
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor

from cortex.engine import CortexEngine
from cortex.engine.ledger import ImmutableLedger
from cortex.mcp.guard import MCPGuard
from cortex.mcp.trust_tools import register_trust_tools
from cortex.mcp.utils import (
    AsyncConnectionPool,
    MCPMetrics,
    MCPServerConfig,
    SimpleAsyncCache,
)

logger = logging.getLogger("cortex.mcp.server")

_MCP_AVAILABLE = False
try:
    from mcp.server.fastmcp import FastMCP

    _MCP_AVAILABLE = True
except ImportError:
    FastMCP = None  # type: ignore
    logger.debug("MCP SDK not installed. Install with: pip install 'cortex-memory[mcp]'")


# ─── Server Context ──────────────────────────────────────────────────


class _MCPContext:
    """Encapsulates the shared state for an MCP server instance.

    Replaces the old ``_state`` dict anti-pattern with a proper class
    that owns its lifecycle.
    """

    __slots__ = ("cfg", "metrics", "executor", "pool", "search_cache", "_initialized")

    def __init__(self, cfg: MCPServerConfig) -> None:
        self.cfg = cfg
        self.metrics = MCPMetrics()
        self.executor = ThreadPoolExecutor(max_workers=cfg.max_workers)
        self.pool = AsyncConnectionPool(cfg.db_path, max_connections=cfg.max_workers)
        self.search_cache = SimpleAsyncCache(maxsize=cfg.query_cache_size)
        self._initialized = False

    async def ensure_ready(self) -> None:
        if not self._initialized:
            await self.pool.initialize()
            self._initialized = True


# ─── Tool Registrators ───────────────────────────────────────────────


def _register_store_tool(mcp: "FastMCP", ctx: _MCPContext) -> None:
    """Register the ``cortex_store`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_store(
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: str = "[]",
        source: str = "",
    ) -> str:
        """Store a fact in CORTEX memory."""
        await ctx.ensure_ready()

        try:
            parsed_tags = json.loads(tags) if tags else []
        except (json.JSONDecodeError, TypeError):
            parsed_tags = []

        try:
            MCPGuard.validate_store(project, content, fact_type, parsed_tags)
        except ValueError as e:
            ctx.metrics.record_error()
            logger.warning("MCP Guard rejected store: %s", e)
            return f"❌ Rejected: {e}"

        async with ctx.pool.acquire() as conn:
            engine = CortexEngine(ctx.cfg.db_path, auto_embed=False)
            engine._conn = conn

            fact_id = await engine.store(
                project,
                content,
                fact_type,
                parsed_tags,
                "stated",
                source or None,
            )

        ctx.metrics.record_request()
        ctx.search_cache.clear()
        return f"✓ Stored fact #{fact_id} in project '{project}'"


def _register_search_tool(mcp: "FastMCP", ctx: _MCPContext) -> None:
    """Register the ``cortex_search`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_search(
        query: str,
        project: str = "",
        top_k: int = 5,
    ) -> str:
        """Search CORTEX memory using semantic + text hybrid search."""
        await ctx.ensure_ready()

        try:
            MCPGuard.validate_search(query)
        except ValueError as e:
            ctx.metrics.record_error()
            logger.warning("MCP Guard rejected search: %s", e)
            return f"❌ Rejected: {e}"

        cache_key = f"{query}:{project}:{top_k}"
        cached_result = ctx.search_cache.get(cache_key)
        if cached_result:
            ctx.metrics.record_request(cached=True)
            return cached_result

        async with ctx.pool.acquire() as conn:
            engine = CortexEngine(ctx.cfg.db_path, auto_embed=False)
            engine._conn = conn

            results = await engine.search(
                query,
                project or None,
                min(max(top_k, 1), 20),
            )

        if not results:
            ctx.search_cache.set(cache_key, "No results found.")
            return "No results found."

        ctx.metrics.record_request()
        lines = [f"Found {len(results)} results:\n"]
        for r in results:
            lines.append(
                f"[#{r.fact_id}] (score: {r.score:.3f}) [{r.project}/{r.fact_type}]\n{r.content}\n"
            )

        output = "\n".join(lines)
        ctx.search_cache.set(cache_key, output)
        return output


def _register_status_tool(mcp: "FastMCP", ctx: _MCPContext) -> None:
    """Register the ``cortex_status`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_status() -> str:
        """Get CORTEX system status and metrics."""
        await ctx.ensure_ready()

        async with ctx.pool.acquire() as conn:
            engine = CortexEngine(ctx.cfg.db_path, auto_embed=False)
            engine._conn = conn
            stats = await engine.stats()

        m_summary = ctx.metrics.get_summary()
        return (
            f"CORTEX Status (Optimized v2):\n"
            f"  Facts: {stats.get('total_facts', 0)} total, "
            f"{stats.get('active_facts', 0)} active\n"
            f"  Projects: {stats.get('project_count', 0)}\n"
            f"  Fact Types: {json.dumps(stats.get('types', {}))}\n"
            f"  DB Size: {stats.get('db_size_mb', 0):.1f} MB\n"
            f"  MCP Metrics: {json.dumps(m_summary, indent=2)}"
        )


def _register_ledger_tool(mcp: "FastMCP", ctx: _MCPContext) -> None:
    """Register the ``cortex_ledger_verify`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_ledger_verify() -> str:
        """Perform a full integrity check on the CORTEX ledger."""
        await ctx.ensure_ready()

        # ImmutableLedger expects a pool, not a single connection
        ledger = ImmutableLedger(ctx.pool)
        report = await ledger.verify_integrity_async()

        if report["valid"]:
            return (
                f"✅ Ledger Integrity: OK\n"
                f"Transactions verified: {report['tx_checked']}\n"
                f"Roots checked: {report['roots_checked']}"
            )
        return (
            f"❌ Ledger Integrity: VIOLATION\n"
            f"Violations: {json.dumps(report['violations'], indent=2)}"
        )


# ─── Factory ─────────────────────────────────────────────────────────


def create_mcp_server(config: MCPServerConfig | None = None) -> "FastMCP":
    """Create and configure an optimized CORTEX MCP server instance.

    Each tool is registered via a dedicated helper, keeping this
    function focused on orchestration (cognitive complexity ≤ 5).
    """
    if not _MCP_AVAILABLE:
        raise ImportError("MCP SDK not installed. Install with: pip install 'cortex-memory[mcp]'")

    cfg = config or MCPServerConfig()
    mcp = FastMCP("CORTEX Trust Engine")
    ctx = _MCPContext(cfg)

    # Core memory tools
    _register_store_tool(mcp, ctx)
    _register_search_tool(mcp, ctx)
    _register_status_tool(mcp, ctx)
    _register_ledger_tool(mcp, ctx)

    # Trust & Compliance tools (EU AI Act Art. 12)
    register_trust_tools(mcp, ctx)

    return mcp


# ─── Global Server Instance ──────────────────────────────────────────

# Default configuration
_default_config = MCPServerConfig()
mcp = create_mcp_server(_default_config)


def run_server(config: MCPServerConfig | None = None) -> None:
    """Start the CORTEX MCP server."""
    global mcp
    if config:
        mcp = create_mcp_server(config)

    cfg = config or _default_config

    if cfg.transport == "sse":
        logger.info("Starting CORTEX MCP server v2 (SSE) on %s:%d", cfg.host, cfg.port)
        mcp.run(transport="sse", host=cfg.host, port=cfg.port)
    else:
        logger.info("Starting CORTEX MCP server v2 (stdio)")
        mcp.run()

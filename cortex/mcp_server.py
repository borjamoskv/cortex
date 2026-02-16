from __future__ import annotations

import atexit
import json
import logging
import os
from functools import lru_cache
from typing import List, Optional

logger = logging.getLogger("cortex.mcp")

__all__ = ["create_mcp_server", "run_server"]

# ─── Server Setup ─────────────────────────────────────────────────────

_MCP_AVAILABLE = False
try:
    from mcp.server.fastmcp import FastMCP
    _MCP_AVAILABLE = True
except ImportError:
    FastMCP = None  # type: ignore
    logger.debug("MCP SDK not installed. Install with: pip install 'cortex-memory[mcp]'")


def create_mcp_server(db_path: str = "~/.cortex/cortex.db") -> "FastMCP":
    """Create and configure a CORTEX MCP server instance."""
    if not _MCP_AVAILABLE:
        raise ImportError(
            "MCP SDK not installed. Install with: pip install mcp\n"
            "Or: pip install 'cortex-memory[mcp]'"
        )

    from cortex.engine import CortexEngine
    from cortex.ledger import ImmutableLedger

    mcp = FastMCP(
        "CORTEX Memory",
        description="Sovereign memory infrastructure for AI agents. "
        "Store, search, and recall facts with semantic search and temporal queries.",
    )

    # Resolve path once
    full_db_path = os.path.expanduser(db_path)
    
    # Lazy engine initialization
    _state: dict = {}

    def get_engine() -> CortexEngine:
        if "engine" not in _state:
            eng = CortexEngine(db_path=full_db_path)
            eng.init_db()
            _state["engine"] = eng
            atexit.register(eng.close)
        return _state["engine"]

    @lru_cache(maxsize=128)
    def cached_search(query: str, project: Optional[str], top_k: int):
        engine = get_engine()
        return engine.search(query=query, project=project, top_k=top_k)

    # ─── Tools ────────────────────────────────────────────────────

    @mcp.tool()
    def cortex_store(
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: str = "[]",
        source: str = "",
    ) -> str:
        """Store a fact in CORTEX memory."""
        engine = get_engine()
        try:
            parsed_tags = json.loads(tags) if tags else []
        except json.JSONDecodeError:
            parsed_tags = []

        fact_id = engine.store(
            project=project,
            content=content,
            fact_type=fact_type,
            tags=parsed_tags,
            source=source or None,
        )
        # Invalidate search cache on store
        cached_search.cache_clear()
        return f"✓ Stored fact #{fact_id} in project '{project}'"

    @mcp.tool()
    def cortex_batch_store(
        project: str,
        facts_json: str,
    ) -> str:
        """Store multiple facts in a single transaction.
        
        Args:
            project: Project/namespace for the facts.
            facts_json: JSON array of objects: [{"content": "...", "type": "...", "tags": [...], "source": "..."}]
        """
        engine = get_engine()
        try:
            facts = json.loads(facts_json)
        except json.JSONDecodeError:
            return "Error: Invalid JSON input for facts_json"

        results = []
        with engine.get_connection() as conn:
            for f in facts:
                fid = engine.store(
                    project=project,
                    content=f.get("content", ""),
                    fact_type=f.get("type", "knowledge"),
                    tags=f.get("tags", []),
                    source=f.get("source"),
                )
                results.append(fid)
        
        cached_search.cache_clear()
        return f"✓ Stored {len(results)} facts in project '{project}' (IDs: {results})"

    @mcp.tool()
    def cortex_search(
        query: str,
        project: str = "",
        top_k: int = 5,
    ) -> str:
        """Search CORTEX memory using semantic + text hybrid search."""
        results = cached_search(query, project or None, min(max(top_k, 1), 20))

        if not results:
            return "No results found."

        lines = [f"Found {len(results)} results:\n"]
        for r in results:
            lines.append(
                f"[#{r.fact_id}] (score: {r.score:.3f}) "
                f"[{r.project}/{r.fact_type}]\n{r.content}\n"
            )
        return "\n".join(lines)

    @mcp.tool()
    def cortex_recall(
        project: str,
        limit: int = 20,
    ) -> str:
        """Load all active facts for a project."""
        engine = get_engine()
        facts = engine.recall(project=project, limit=limit)

        if not facts:
            return f"No facts found for project '{project}'."

        lines = [f"📁 {project} — {len(facts)} facts:\n"]
        for f in facts:
            try:
                tags = f.tags if isinstance(f.tags, list) else json.loads(f.tags) if isinstance(f.tags, str) else []
            except (json.JSONDecodeError, TypeError):
                tags = []
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            lines.append(f"  #{f.id} [{f.fact_type}]{tag_str}: {f.content[:200]}")
        return "\n".join(lines)

    @mcp.tool()
    def cortex_ledger_status() -> str:
        """Check the cryptographic integrity of the CORTEX ledger.
        
        Returns:
            Integrity status and violation details if any.
        """
        engine = get_engine()
        ledger = ImmutableLedger(engine.get_connection())
        report = ledger.verify_integrity()
        
        if report["valid"]:
            return (f"✅ Ledger Integrity: OK\n"
                    f"Transactions verified: {report['tx_checked']}\n"
                    f"Merkle checkpoints verified: {report['roots_checked']}")
        else:
            return (f"❌ Ledger Integrity: VIOLATION DETECTED\n"
                    f"Violations: {json.dumps(report['violations'], indent=2)}")

    @mcp.tool()
    def cortex_status() -> str:
        """Get CORTEX system status and statistics."""
        engine = get_engine()
        stats = engine.stats()
        return (
            f"CORTEX Status (MCP v2):\n"
            f"  Facts: {stats.get('total_facts', 0)} total, "
            f"{stats.get('active_facts', 0)} active\n"
            f"  Projects: {stats.get('projects', 0)}\n"
            f"  Transactions: {stats.get('transactions', 0)}\n"
            f"  DB Size: {stats.get('db_size_mb', 0):.1f} MB\n"
            f"  Search Cache: {cached_search.cache_info()}"
        )

    @mcp.tool()
    def cortex_timeline_reconstruct(
        tx_id: int,
        project: str = "",
    ) -> str:
        """Reconstruct the database state at a specific transaction ID.
        
        Args:
            tx_id: The transaction ID to reconstruct.
            project: Optional filter by project.
        """
        engine = get_engine()
        try:
            facts = engine.reconstruct_state(tx_id, project=project or None)
        except ValueError as e:
            return f"Error: {e}"

        if not facts:
            return f"No active facts at TX #{tx_id}."

        lines = [f"🕰 State at TX #{tx_id}:\n"]
        for f in facts:
            lines.append(f"  #{f.id} [{f.project}/{f.fact_type}]: {f.content[:150]}")
        return "\n".join(lines)

    @mcp.tool()
    def cortex_snapshot_create(
        name: str,
    ) -> str:
        """Create a full physical database snapshot for safe-keeping.
        
        Args:
            name: A descriptive name for the snapshot.
        """
        from cortex.snapshots import SnapshotManager
        from cortex.ledger import ImmutableLedger
        
        engine = get_engine()
        conn = engine.get_connection()
        
        ledger = ImmutableLedger(conn)
        latest_tx = conn.execute("SELECT id FROM transactions ORDER BY id DESC LIMIT 1").fetchone()
        tx_id = latest_tx[0] if latest_tx else 0
        
        root_row = conn.execute("SELECT root_hash FROM merkle_roots ORDER BY id DESC LIMIT 1").fetchone()
        merkle_root = root_row[0] if root_row else "0xGENESIS"
        
        sm = SnapshotManager(db_path=full_db_path)
        snap = sm.create_snapshot(name, tx_id, merkle_root)
        
        return (f"✓ Snapshot '{name}' created.\n"
                f"  TX ID: {snap.tx_id}\n"
                f"  Path: {snap.path}")

    # ─── Resources ────────────────────────────────────────────────

    @mcp.resource("cortex://projects")
    def list_projects() -> str:
        """List all projects in CORTEX memory."""
        engine = get_engine()
        conn = engine.get_connection()
        rows = conn.execute(
            "SELECT DISTINCT project FROM facts WHERE valid_until IS NULL "
            "ORDER BY project"
        ).fetchall()
        projects = [r[0] for r in rows]
        return json.dumps({"projects": projects, "count": len(projects)})

    return mcp


def run_server(db_path: str = "~/.cortex/cortex.db") -> None:
    """Start the CORTEX MCP server (stdio transport)."""
    mcp = create_mcp_server(db_path)
    logger.info("Starting CORTEX MCP server v2 (stdio transport)...")
    mcp.run()

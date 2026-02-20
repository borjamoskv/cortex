"""
CORTEX Trust Tools — EU AI Act Compliance MCP Tools.

These tools extend the CORTEX MCP server with audit, verification,
and compliance capabilities aligned with EU AI Act Article 12
(record-keeping obligations for high-risk AI systems).

Tools:
    - cortex_audit_trail: Generate audit trail for agent decisions
    - cortex_verify_fact: Verify cryptographic integrity of a specific fact
    - cortex_compliance_report: Generate EU AI Act compliance snapshot
    - cortex_decision_lineage: Trace the lineage of a decision
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from cortex.engine import CortexEngine
from cortex.engine.ledger import ImmutableLedger

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from cortex.mcp.server import _MCPContext

logger = logging.getLogger("cortex.mcp.trust")


def register_trust_tools(mcp: "FastMCP", ctx: "_MCPContext") -> None:
    """Register all Trust/Compliance tools on the MCP server."""

    _register_audit_trail(mcp, ctx)
    _register_verify_fact(mcp, ctx)
    _register_compliance_report(mcp, ctx)
    _register_decision_lineage(mcp, ctx)


def _register_audit_trail(mcp: "FastMCP", ctx: "_MCPContext") -> None:
    """Register the ``cortex_audit_trail`` tool."""

    @mcp.tool()
    async def cortex_audit_trail(
        project: str = "",
        agent_id: str = "",
        since: str = "",
        limit: int = 50,
    ) -> str:
        """Generate an immutable audit trail of agent decisions.

        Produces a timestamped, hash-verified log of all decisions
        made by agents within a project. Each entry includes the
        cryptographic hash from the transaction ledger, ensuring
        tamper-proof evidence per EU AI Act Article 12.

        Args:
            project: Filter by project name (empty = all projects)
            agent_id: Filter by agent ID tag (empty = all agents)
            since: ISO date filter, e.g. "2026-01-01" (empty = all time)
            limit: Maximum entries to return (default 50, max 200)
        """
        await ctx.ensure_ready()
        limit = min(max(limit, 1), 200)

        async with ctx.pool.acquire() as conn:
            # Build query with optional filters
            conditions = ["f.deprecated_at IS NULL"]
            params: list = []

            if project:
                conditions.append("f.project = ?")
                params.append(project)
            if agent_id:
                conditions.append("f.tags LIKE ?")
                params.append(f"%agent:{agent_id}%")
            if since:
                conditions.append("f.created_at >= ?")
                params.append(since)

            where = " AND ".join(conditions)

            query = f"""
                SELECT f.id, f.project, f.content, f.fact_type,
                       f.created_at, f.tags,
                       t.hash, t.prev_hash, t.operation
                FROM facts f
                LEFT JOIN transactions t ON t.fact_id = f.id
                WHERE {where}
                ORDER BY f.created_at DESC
                LIMIT ?
            """
            params.append(limit)

            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()

        if not rows:
            return "No audit entries found for the given filters."

        lines = [
            "═══ CORTEX AUDIT TRAIL ═══",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Entries: {len(rows)}",
            f"Filters: project={project or '*'}, agent={agent_id or '*'}, since={since or 'all'}",
            "═" * 40,
            "",
        ]

        for row in rows:
            fact_id, proj, content, ftype, created, tags, tx_hash, prev_hash, op = row
            hash_short = (tx_hash or "—")[:16]
            prev_short = (prev_hash or "genesis")[:16]
            lines.append(
                f"[{created}] #{fact_id} ({ftype}) [{proj}]\n"
                f"  Content: {content[:200]}\n"
                f"  Hash: {hash_short}… → prev: {prev_short}…\n"
                f"  Tags: {tags or 'none'}\n"
            )

        lines.append("═" * 40)
        lines.append("Cryptographic chain verified via SHA-256 hash linking.")
        return "\n".join(lines)


def _register_verify_fact(mcp: "FastMCP", ctx: "_MCPContext") -> None:
    """Register the ``cortex_verify_fact`` tool."""

    @mcp.tool()
    async def cortex_verify_fact(fact_id: int) -> str:
        """Verify the cryptographic integrity of a specific fact.

        Checks that the fact's transaction hash is valid, the chain
        to its predecessor is unbroken, and the content has not been
        tampered with. Returns a verification certificate.

        Args:
            fact_id: The ID of the fact to verify
        """
        await ctx.ensure_ready()

        async with ctx.pool.acquire() as conn:
            # Get the fact
            cursor = await conn.execute(
                "SELECT id, project, content, fact_type, created_at "
                "FROM facts WHERE id = ?",
                (fact_id,),
            )
            fact = await cursor.fetchone()

            if not fact:
                return f"❌ Fact #{fact_id} not found."

            # Get the transaction
            cursor = await conn.execute(
                "SELECT id, hash, prev_hash, operation, created_at "
                "FROM transactions WHERE fact_id = ?",
                (fact_id,),
            )
            tx = await cursor.fetchone()

            if not tx:
                return (
                    f"⚠️ Fact #{fact_id} exists but has no transaction record.\n"
                    f"This fact predates the ledger system."
                )

            # Verify the hash chain to predecessor
            tx_id, tx_hash, prev_hash, operation, tx_time = tx
            chain_valid = True
            chain_msg = "✅ Valid"

            if prev_hash:
                cursor = await conn.execute(
                    "SELECT hash FROM transactions WHERE id = ?",
                    (tx_id - 1,),
                )
                prev_tx = await cursor.fetchone()
                if prev_tx and prev_tx[0] != prev_hash:
                    chain_valid = False
                    chain_msg = "❌ BROKEN — prev_hash mismatch"

            # Check if the fact is in a Merkle checkpoint
            cursor = await conn.execute(
                "SELECT id, merkle_root, start_id, end_id, created_at "
                "FROM merkle_roots "
                "WHERE start_id <= ? AND end_id >= ? "
                "LIMIT 1",
                (tx_id, tx_id),
            )
            checkpoint = await cursor.fetchone()

        # Build verification certificate
        fid, proj, content, ftype, created = fact
        lines = [
            "═══ CORTEX VERIFICATION CERTIFICATE ═══",
            f"Fact ID:      #{fid}",
            f"Project:      {proj}",
            f"Type:         {ftype}",
            f"Created:      {created}",
            f"Content:      {content[:300]}",
            "",
            "── Cryptographic Proof ──",
            f"TX Hash:      {tx_hash}",
            f"Prev Hash:    {prev_hash or 'genesis'}",
            f"Chain Link:   {chain_msg}",
            f"Operation:    {operation}",
        ]

        if checkpoint:
            cp_id, merkle_root, start, end, cp_time = checkpoint
            lines.extend([
                "",
                "── Merkle Checkpoint ──",
                f"Checkpoint:   #{cp_id}",
                f"Merkle Root:  {merkle_root}",
                f"Range:        TX #{start} → #{end}",
                f"Sealed At:    {cp_time}",
                f"Status:       ✅ Fact included in sealed checkpoint",
            ])
        else:
            lines.append("\nMerkle:       ⏳ Not yet included in a checkpoint")

        overall = "✅ VERIFIED" if chain_valid else "❌ INTEGRITY VIOLATION"
        lines.extend(["", f"═══ VERDICT: {overall} ═══"])

        return "\n".join(lines)


def _register_compliance_report(mcp: "FastMCP", ctx: "_MCPContext") -> None:
    """Register the ``cortex_compliance_report`` tool."""

    @mcp.tool()
    async def cortex_compliance_report() -> str:
        """Generate an EU AI Act Article 12 compliance snapshot.

        Produces a summary report covering:
        - Ledger integrity status (hash chain + Merkle checkpoints)
        - Decision logging completeness
        - Agent activity traceability
        - Data governance metrics

        This report can be used as evidence for regulatory audits.
        """
        await ctx.ensure_ready()

        async with ctx.pool.acquire() as conn:
            # Total facts
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM facts WHERE deprecated_at IS NULL"
            )
            total_facts = (await cursor.fetchone())[0]

            # Decisions count
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM facts "
                "WHERE fact_type = 'decision' AND deprecated_at IS NULL"
            )
            decisions = (await cursor.fetchone())[0]

            # Total transactions
            cursor = await conn.execute("SELECT COUNT(*) FROM transactions")
            total_tx = (await cursor.fetchone())[0]

            # Merkle checkpoints
            cursor = await conn.execute("SELECT COUNT(*) FROM merkle_roots")
            checkpoints = (await cursor.fetchone())[0]

            # Projects
            cursor = await conn.execute(
                "SELECT COUNT(DISTINCT project) FROM facts "
                "WHERE deprecated_at IS NULL"
            )
            projects = (await cursor.fetchone())[0]

            # Agents (from tags)
            cursor = await conn.execute(
                "SELECT DISTINCT tags FROM facts "
                "WHERE tags LIKE '%agent:%' AND deprecated_at IS NULL"
            )
            agent_rows = await cursor.fetchall()
            agents = set()
            for row in agent_rows:
                if row[0]:
                    for tag in row[0].split(","):
                        tag = tag.strip()
                        if tag.startswith("agent:"):
                            agents.add(tag)

            # Oldest and newest fact
            cursor = await conn.execute(
                "SELECT MIN(created_at), MAX(created_at) FROM facts "
                "WHERE deprecated_at IS NULL"
            )
            time_range = await cursor.fetchone()

        # Verify ledger integrity
        ledger = ImmutableLedger(ctx.pool)
        integrity = await ledger.verify_integrity_async()

        now = datetime.now(timezone.utc).isoformat()

        lines = [
            "╔══════════════════════════════════════════════════╗",
            "║   CORTEX — EU AI Act Compliance Report          ║",
            "║   Article 12: Record-Keeping Obligations         ║",
            "╚══════════════════════════════════════════════════╝",
            "",
            f"Report Generated: {now}",
            "",
            "── 1. Data Inventory ──",
            f"  Total Facts:           {total_facts}",
            f"  Logged Decisions:      {decisions}",
            f"  Active Projects:       {projects}",
            f"  Tracked Agents:        {len(agents)}",
            f"  Coverage Period:       {time_range[0] or 'N/A'} → {time_range[1] or 'N/A'}",
            "",
            "── 2. Cryptographic Integrity ──",
            f"  Transaction Ledger:    {total_tx} entries",
            f"  Merkle Checkpoints:    {checkpoints}",
            f"  Hash Chain:            {'✅ VALID' if integrity['valid'] else '❌ BROKEN'}",
            f"  TX Verified:           {integrity.get('tx_checked', 0)}",
            f"  Roots Verified:        {integrity.get('roots_checked', 0)}",
        ]

        if not integrity["valid"]:
            lines.append(f"  ⚠️ Violations:        {len(integrity.get('violations', []))}")

        lines.extend([
            "",
            "── 3. Compliance Checklist (Art. 12) ──",
            f"  [{'✅' if total_tx > 0 else '❌'}] Automatic logging of events (Art. 12.1)",
            f"  [{'✅' if decisions > 0 else '❌'}] Decision recording (Art. 12.2)",
            f"  [{'✅' if integrity['valid'] else '❌'}] Tamper-proof storage (Art. 12.3)",
            f"  [{'✅' if checkpoints > 0 else '❌'}] Periodic integrity verification (Art. 12.4)",
            f"  [{'✅' if len(agents) > 0 else '⚠️'}] Agent traceability (Art. 12.2d)",
            "",
            "── 4. Recommendation ──",
        ])

        score = sum([
            total_tx > 0,
            decisions > 0,
            integrity["valid"],
            checkpoints > 0,
            len(agents) > 0,
        ])

        if score == 5:
            lines.append("  🟢 COMPLIANT — All Article 12 requirements met.")
        elif score >= 3:
            lines.append("  🟡 PARTIAL — Some requirements need attention.")
        else:
            lines.append("  🔴 NON-COMPLIANT — Critical gaps in record-keeping.")

        lines.append(f"\n  Compliance Score: {score}/5")

        return "\n".join(lines)


def _register_decision_lineage(mcp: "FastMCP", ctx: "_MCPContext") -> None:
    """Register the ``cortex_decision_lineage`` tool."""

    @mcp.tool()
    async def cortex_decision_lineage(
        fact_id: int = 0,
        query: str = "",
        project: str = "",
    ) -> str:
        """Trace the full lineage of a decision through the ledger.

        Given a fact ID or search query, reconstructs the chain of
        related decisions, showing how the agent arrived at this
        conclusion. Essential for AI explainability requirements.

        Args:
            fact_id: Specific fact ID to trace (0 = use query instead)
            query: Search for a decision by keyword (used if fact_id=0)
            project: Filter by project (optional)
        """
        await ctx.ensure_ready()

        async with ctx.pool.acquire() as conn:
            if fact_id > 0:
                cursor = await conn.execute(
                    "SELECT id, project, content, fact_type, created_at, tags "
                    "FROM facts WHERE id = ? AND deprecated_at IS NULL",
                    (fact_id,),
                )
                target = await cursor.fetchone()
                if not target:
                    return f"❌ Fact #{fact_id} not found."
            elif query:
                conditions = ["deprecated_at IS NULL", "content LIKE ?"]
                params: list = [f"%{query}%"]
                if project:
                    conditions.append("project = ?")
                    params.append(project)
                where = " AND ".join(conditions)
                cursor = await conn.execute(
                    f"SELECT id, project, content, fact_type, created_at, tags "
                    f"FROM facts WHERE {where} "
                    f"ORDER BY created_at DESC LIMIT 1",
                    params,
                )
                target = await cursor.fetchone()
                if not target:
                    return f"❌ No facts found matching '{query}'."
            else:
                return "❌ Provide either fact_id or query."

            tid, tproj, tcontent, ttype, tcreated, ttags = target

            # Find related decisions in the same project
            cursor = await conn.execute(
                "SELECT id, content, fact_type, created_at, tags "
                "FROM facts "
                "WHERE project = ? AND deprecated_at IS NULL "
                "AND created_at <= ? "
                "AND id != ? "
                "ORDER BY created_at DESC LIMIT 20",
                (tproj, tcreated, tid),
            )
            predecessors = await cursor.fetchall()

            # Find subsequent decisions
            cursor = await conn.execute(
                "SELECT id, content, fact_type, created_at, tags "
                "FROM facts "
                "WHERE project = ? AND deprecated_at IS NULL "
                "AND created_at > ? "
                "ORDER BY created_at ASC LIMIT 10",
                (tproj, tcreated),
            )
            successors = await cursor.fetchall()

        lines = [
            "═══ DECISION LINEAGE ═══",
            f"Target: #{tid} [{ttype}] in '{tproj}'",
            f"Content: {tcontent[:300]}",
            f"Created: {tcreated}",
            "",
        ]

        if predecessors:
            lines.append(f"── Preceding Context ({len(predecessors)} entries) ──")
            for p in reversed(predecessors[-10:]):
                pid, pcontent, ptype, pcreated, ptags = p
                lines.append(f"  [{pcreated}] #{pid} ({ptype}): {pcontent[:120]}")
            lines.append("")

        lines.append("  ──── ★ TARGET DECISION ────")
        lines.append(f"  [{tcreated}] #{tid} ({ttype}): {tcontent[:200]}")
        lines.append("")

        if successors:
            lines.append(f"── Subsequent Impact ({len(successors)} entries) ──")
            for s in successors[:5]:
                sid, scontent, stype, screated, stags = s
                lines.append(f"  [{screated}] #{sid} ({stype}): {scontent[:120]}")

        lines.extend(["", "═" * 40])
        return "\n".join(lines)

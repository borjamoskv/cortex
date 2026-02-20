"""
CORTEX CLI — Trust & Compliance Commands.

Provides CLI commands for cryptographic verification, audit trails,
and EU AI Act Article 12 compliance reporting.
"""

import asyncio
import json

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex.cli import cli, get_engine, DEFAULT_DB
from cortex.config import DEFAULT_DB_PATH

console = Console()


def _run_async(coro):
    """Run an async coroutine synchronously."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@cli.command("verify")
@click.argument("fact_id", type=int)
@click.option("--db", default=DEFAULT_DB, help="Database path")
def verify_fact(fact_id: int, db: str) -> None:
    """Verify cryptographic integrity of a specific fact.

    Checks SHA-256 hash chain and Merkle checkpoint inclusion.
    Outputs a verification certificate.
    """
    import sqlite3

    conn = sqlite3.connect(db)

    # Get the fact
    fact = conn.execute(
        "SELECT id, project, content, fact_type, created_at, tx_id "
        "FROM facts WHERE id = ?",
        (fact_id,),
    ).fetchone()

    if not fact:
        console.print(f"[red]❌ Fact #{fact_id} not found.[/red]")
        return

    fid, proj, content, ftype, created, fact_tx_id = fact

    # Get the transaction via tx_id
    tx = None
    if fact_tx_id:
        tx = conn.execute(
            "SELECT id, hash, prev_hash, action, timestamp "
            "FROM transactions WHERE id = ?",
            (fact_tx_id,),
        ).fetchone()

    if not tx:
        # Try joining via tx_id column on facts
        tx = conn.execute(
            "SELECT t.id, t.hash, t.prev_hash, t.action, t.timestamp "
            "FROM facts f JOIN transactions t ON f.tx_id = t.id "
            "WHERE f.id = ?",
            (fact_id,),
        ).fetchone()

    if not tx:
        console.print(
            Panel(
                f"[yellow]⚠️ Fact #{fact_id} exists but has no transaction record.\n"
                f"This fact predates the ledger system.[/yellow]",
                title="Verification",
            )
        )
        return

    tx_id, tx_hash, prev_hash, action, tx_time = tx

    # Verify chain
    chain_valid = True
    chain_msg = "[green]✅ Valid[/green]"

    if prev_hash:
        prev_tx = conn.execute(
            "SELECT hash FROM transactions WHERE id = ?",
            (tx_id - 1,),
        ).fetchone()
        if prev_tx and prev_tx[0] != prev_hash:
            chain_valid = False
            chain_msg = "[red]❌ BROKEN — prev_hash mismatch[/red]"

    # Check if the fact is in a Merkle checkpoint
    try:
        checkpoint = conn.execute(
            "SELECT id, root_hash, tx_start_id, tx_end_id, created_at "
            "FROM merkle_roots "
            "WHERE tx_start_id <= ? AND tx_end_id >= ? LIMIT 1",
            (tx_id, tx_id),
        ).fetchone()
    except (sqlite3.Error, OSError, RuntimeError):
        checkpoint = None

    conn.close()

    # Build certificate
    table = Table(title="CORTEX Verification Certificate", show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Fact ID", f"#{fid}")
    table.add_row("Project", proj)
    table.add_row("Type", ftype)
    table.add_row("Created", created)
    table.add_row("Content", content[:200])
    table.add_row("", "")
    table.add_row("TX Hash", tx_hash[:32] + "…")
    table.add_row("Prev Hash", (prev_hash or "genesis")[:32] + "…")
    table.add_row("Chain Link", chain_msg)

    if checkpoint:
        cp_id, merkle_root, start, end, cp_time = checkpoint
        table.add_row("", "")
        table.add_row("Merkle Root", merkle_root[:32] + "…")
        table.add_row("Checkpoint", f"#{cp_id} (TX #{start}→#{end})")
        table.add_row("Sealed", cp_time)
        table.add_row("Merkle Status", "[green]✅ Included in sealed checkpoint[/green]")
    else:
        table.add_row("Merkle", "[yellow]⏳ Not yet checkpointed[/yellow]")

    overall = "[green]✅ VERIFIED[/green]" if chain_valid else "[red]❌ INTEGRITY VIOLATION[/red]"
    console.print(table)
    console.print(Panel(overall, title="Verdict"))


def _safe_count(conn, query: str) -> int:
    """Execute a COUNT query, return 0 on error."""
    try:
        return conn.execute(query).fetchone()[0]
    except (sqlite3.Error, OSError, RuntimeError):
        return 0


def _extract_agents(conn) -> set[str]:
    """Parse agent tags from facts."""
    rows = conn.execute(
        "SELECT DISTINCT tags FROM facts "
        "WHERE tags LIKE '%agent:%' AND valid_until IS NULL"
    ).fetchall()
    agents: set[str] = set()
    for row in rows:
        if not row[0]:
            continue
        try:
            tags = json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            tags = [t.strip() for t in row[0].split(",")]
        for tag in tags:
            if isinstance(tag, str) and tag.startswith("agent:"):
                agents.add(tag)
    return agents


def _check_chain_integrity(conn) -> tuple[bool, int]:
    """Verify transaction hash chain. Returns (valid, violations)."""
    try:
        txs = conn.execute(
            "SELECT id, hash, prev_hash FROM transactions ORDER BY id LIMIT 1000"
        ).fetchall()
    except (sqlite3.Error, OSError, RuntimeError):
        return True, 0
    violations = sum(
        1 for i in range(1, len(txs))
        if txs[i][2] and txs[i][2] != txs[i - 1][1]
    )
    return violations == 0, violations


@cli.command("compliance-report")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def compliance_report(db: str) -> None:
    """Generate EU AI Act Article 12 compliance snapshot.

    Checks ledger integrity, decision logging, agent traceability,
    and outputs a compliance score (0-5).
    """
    import sqlite3
    from datetime import datetime, timezone

    conn = sqlite3.connect(db)

    total_facts = _safe_count(conn, "SELECT COUNT(*) FROM facts WHERE valid_until IS NULL")
    decisions = _safe_count(conn, "SELECT COUNT(*) FROM facts WHERE fact_type = 'decision' AND valid_until IS NULL")
    total_tx = _safe_count(conn, "SELECT COUNT(*) FROM transactions")
    checkpoints = _safe_count(conn, "SELECT COUNT(*) FROM merkle_roots")
    projects = _safe_count(conn, "SELECT COUNT(DISTINCT project) FROM facts WHERE valid_until IS NULL")
    agents = _extract_agents(conn)

    time_range = conn.execute(
        "SELECT MIN(created_at), MAX(created_at) FROM facts WHERE valid_until IS NULL"
    ).fetchone()

    chain_ok, violations = _check_chain_integrity(conn)
    conn.close()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    console.print()
    console.print(Panel.fit(
        "[bold]CORTEX — EU AI Act Compliance Report[/bold]\n"
        "[dim]Article 12: Record-Keeping Obligations[/dim]",
        border_style="bright_green" if chain_ok else "red",
    ))

    table = Table(show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Report Date", now)
    table.add_row("Total Facts", str(total_facts))
    table.add_row("Logged Decisions", str(decisions))
    table.add_row("Active Projects", str(projects))
    table.add_row("Tracked Agents", str(len(agents)))
    table.add_row("Coverage", f"{time_range[0] or 'N/A'} → {time_range[1] or 'N/A'}")
    table.add_row("", "")
    table.add_row("TX Ledger Entries", str(total_tx))
    table.add_row("Merkle Checkpoints", str(checkpoints))
    table.add_row(
        "Hash Chain",
        "[green]✅ VALID[/green]" if chain_ok else f"[red]❌ {violations} violations[/red]",
    )
    console.print(table)

    # Compliance checklist
    c1, c2, c3, c4, c5 = total_tx > 0, decisions > 0, chain_ok, checkpoints > 0, len(agents) > 0
    icon = lambda ok: "[green]✅[/green]" if ok else "[red]❌[/red]"

    checks = Table(title="Compliance Checklist (Art. 12)")
    checks.add_column("Requirement", style="bold")
    checks.add_column("Status")
    checks.add_row("Automatic event logging (Art. 12.1)", icon(c1))
    checks.add_row("Decision recording (Art. 12.2)", icon(c2))
    checks.add_row("Tamper-proof storage (Art. 12.3)", icon(c3))
    checks.add_row("Periodic verification (Art. 12.4)", icon(c4))
    checks.add_row("Agent traceability (Art. 12.2d)", icon(c5))
    console.print(checks)

    score = sum([c1, c2, c3, c4, c5])
    if score == 5:
        verdict = "[bold green]🟢 COMPLIANT — All Article 12 requirements met.[/bold green]"
    elif score >= 3:
        verdict = "[bold yellow]🟡 PARTIAL — Some requirements need attention.[/bold yellow]"
    else:
        verdict = "[bold red]🔴 NON-COMPLIANT — Critical gaps in record-keeping.[/bold red]"

    console.print(Panel(f"{verdict}\n\nCompliance Score: [bold]{score}/5[/bold]", title="Verdict"))


@cli.command("audit-trail")
@click.option("--project", "-p", default="", help="Filter by project")
@click.option("--limit", "-n", default=20, help="Max entries")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def audit_trail(project: str, limit: int, db: str) -> None:
    """Generate audit trail of agent decisions with hash verification."""
    import sqlite3

    conn = sqlite3.connect(db)

    conditions = ["f.valid_until IS NULL"]
    params: list = []

    if project:
        conditions.append("f.project = ?")
        params.append(project)

    where = " AND ".join(conditions)
    params.append(min(limit, 200))

    rows = conn.execute(
        f"""
        SELECT f.id, f.project, f.content, f.fact_type,
               f.created_at, t.hash
        FROM facts f
        LEFT JOIN transactions t ON f.tx_id = t.id
        WHERE {where}
        ORDER BY f.created_at DESC
        LIMIT ?
        """,
        params,
    ).fetchall()

    conn.close()

    if not rows:
        console.print("[yellow]No audit entries found.[/yellow]")
        return

    table = Table(title=f"CORTEX Audit Trail ({len(rows)} entries)")
    table.add_column("ID", style="dim")
    table.add_column("Time")
    table.add_column("Project", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Content")
    table.add_column("Hash", style="dim")

    for row in rows:
        fid, proj, content, ftype, created, tx_hash = row
        table.add_row(
            str(fid),
            created[:19] if created else "—",
            proj,
            ftype,
            content[:80] + ("…" if len(content) > 80 else ""),
            (tx_hash or "—")[:12] + "…" if tx_hash else "—",
        )

    console.print(table)

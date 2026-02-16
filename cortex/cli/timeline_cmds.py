"""CLI commands: timeline log, checkout, snapshot."""

from __future__ import annotations

import asyncio
import click
from rich.table import Table

from cortex.cli import cli, console, DEFAULT_DB
from cortex.api_deps import get_engine

@cli.group()
def timeline():
    """Navigate the CORTEX timeline and manage snapshots."""
    pass

@timeline.command("log")
@click.option("--limit", "-n", default=20, help="Number of transactions")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def timeline_log(limit, db):
    """Show the transaction history ledger."""
    async def _timeline_log_async():
        engine = get_engine(db)
        try:
            conn = await engine.get_conn()
            cursor = await conn.execute(
                "SELECT id, project, action, hash, timestamp FROM transactions ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            if not rows:
                console.print("[yellow]No transactions found.[/]")
                return
            table = Table(title="📜 Transaction Ledger")
            table.add_column("TX ID", style="bold", width=8)
            table.add_column("Project", style="cyan", width=15)
            table.add_column("Action", style="magenta", width=10)
            table.add_column("Hash", style="dim", width=16)
            table.add_column("Timestamp", width=20)
            for row in rows:
                table.add_row(f"#{row[0]}", row[1], row[2], row[3][:12] + "...", row[4])
            console.print(table)
        finally:
            await engine.close()
            
    asyncio.run(_timeline_log_async())

@timeline.command("checkout")
@click.argument("tx_id", type=int)
@click.option("--project", "-p", default=None, help="Filter by project")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def timeline_checkout(tx_id, project, db):
    """Reconstruct state at a specific transaction ID."""
    async def _timeline_checkout_async():
        engine = get_engine(db)
        try:
            with console.status(f"[bold blue]Reconstructing state at TX #{tx_id}...[/]"):
                facts = await engine.reconstruct_state(tx_id, project=project)
            if not facts:
                console.print(f"[yellow]No active facts at TX #{tx_id}.[/]")
                return
            title = f"🕰 State at TX #{tx_id}"
            if project:
                title += f" (Project: {project})"
            table = Table(title=title)
            table.add_column("ID", style="bold", width=5)
            table.add_column("Project", style="cyan", width=15)
            table.add_column("Type", style="magenta", width=10)
            table.add_column("Content", width=50)
            table.add_column("Score", style="green", width=6)
            for f in facts:
                table.add_row(
                    str(f.id), f.project, f.fact_type,
                    f.content[:50] + "..." if len(f.content) > 50 else f.content,
                    f"{f.consensus_score:.2f}"
                )
            console.print(table)
        finally:
            await engine.close()
            
    asyncio.run(_timeline_checkout_async())

@timeline.group("snapshot")
def timeline_snapshot():
    """Manage physical database snapshots."""
    pass

@timeline_snapshot.command("create")
@click.argument("name")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def snapshot_create(name, db):
    """Create a new physical snapshot."""
    async def _snapshot_create_async():
        from cortex.engine.ledger import ImmutableLedger
        from cortex.engine.snapshots import SnapshotManager
        engine = get_engine(db)
        try:
            conn = await engine.get_conn()
            # ledger = ImmutableLedger(conn) # Unused but for context
            cursor = await conn.execute("SELECT id FROM transactions ORDER BY id DESC LIMIT 1")
            latest_tx = await cursor.fetchone()
            tx_id = latest_tx[0] if latest_tx else 0
            
            cursor = await conn.execute("SELECT root_hash FROM merkle_roots ORDER BY id DESC LIMIT 1")
            root_row = await cursor.fetchone()
            merkle_root = root_row[0] if root_row else "0xGENESIS"
            
            sm = SnapshotManager(db_path=db)
            with console.status("[bold blue]Creating physical snapshot...[/]"):
                snap = await sm.create_snapshot(name, tx_id, merkle_root)
            console.print(f"[green]✓[/] Snapshot [bold]'{name}'[/] created successfully.")
            console.print(f"  [dim]Path:[/] {snap.path}")
            console.print(f"  [dim]TX ID:[/] {snap.tx_id}")
            console.print(f"  [dim]Size:[/] {snap.size_mb} MB")
        finally:
            await engine.close()
            
    asyncio.run(_snapshot_create_async())

@timeline_snapshot.command("list")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def snapshot_list(db):
    """List all available snapshots."""
    async def _snapshot_list_async():
        from cortex.engine.snapshots import SnapshotManager
        sm = SnapshotManager(db_path=db)
        snaps = await sm.list_snapshots()
        if not snaps:
            console.print("[yellow]No snapshots found.[/]")
            return
        table = Table(title="💾 CORTEX Snapshots")
        table.add_column("Name", style="bold", width=20)
        table.add_column("TX ID", style="cyan", width=8)
        table.add_column("Created At", width=20)
        table.add_column("Size", width=10)
        for s in snaps:
            table.add_row(
                s.name, str(s.tx_id),
                s.created_at[:19].replace("T", " "), f"{s.size_mb} MB"
            )
        console.print(table)
        
    asyncio.run(_snapshot_list_async())

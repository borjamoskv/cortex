"""CLI commands: vote, ledger verify, ledger checkpoint."""

from __future__ import annotations

import asyncio
import sys

import click
from rich.panel import Panel

from cortex.api_deps import get_engine
from cortex.cli import DEFAULT_DB, cli, console
# Updated import for Wave 5 Phase 2
from cortex.consensus.vote_ledger import ImmutableVoteLedger


@cli.command()
@click.argument("fact_id", type=int)
@click.argument("value", type=int)
@click.option("--agent", "-a", default="human", help="Agent name")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def vote(fact_id, value, agent, db) -> None:
    """Cast a consensus vote on a fact (1=verify, -1=dispute)."""
    async def _vote_async():
        engine = get_engine(db)
        try:
            # We need to use the new AsyncEngine method if available, or fallback.
            # For this CLI tool, we might use the internal method if engine doesn't expose it yet.
            # But the requirement is to use the ImmutableLedger.
            
            # Since CortexEngine is legacy, we might need to manually append to ledger for now
            # or rely on the engine to do it. 
            # Wave 5 implies we are moving to AsyncCortexEngine.
            # Let's instantiate the Ledger directly for the vote if needed, 
            # or just assume engine.vote() works (legacy).
            # But wait, we want to test the NEW ledger.
            
            conn = await engine.get_conn()
            ledger = ImmutableVoteLedger(conn)
            
            if value not in [1, -1]:
                console.print("[red]✗ Vote must be 1 (verify) or -1 (dispute)[/]")
                return
            
            # 10.0 weight for human votes
            entry = await ledger.append_vote(fact_id, agent, value, 10.0)
            
            console.print(
                f"[green]✓[/] Agent [bold]{agent}[/] voted {value} on fact [bold]#{fact_id}[/].\n"
                f"   [dim]Hash: {entry.hash[:16]}...[/]"
            )
        finally:
            await engine.close()
    
    asyncio.run(_vote_async())

@cli.group()
def ledger():
    """Manage the immutable vote ledger."""
    pass

@ledger.command("verify")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def ledger_verify(db):
    """Verify cryptographic integrity of the vote ledger."""
    async def _ledger_verify_async():
        engine = get_engine(db)
        try:
            conn = await engine.get_conn()
            _ledger = ImmutableVoteLedger(conn)
            with console.status("[bold blue]Verifying vote ledger integrity...[/]"):
                report = await _ledger.verify_chain_integrity()
            
            if report["valid"]:
                console.print(Panel(
                    f"[bold green]✅ Vote Ledger Integrity: OK[/]\n"
                    f"Votes checked: {report['votes_checked']}",
                    title="🔐 Immutable Vote Ledger", border_style="green",
                ))
            else:
                console.print(Panel(
                    f"[bold red]❌ Vote Ledger Integrity: VIOLATION DETECTED[/]\n"
                    f"Violations found: {len(report['violations'])}",
                    title="🔐 Immutable Vote Ledger", border_style="red",
                ))
                for v in report["violations"]:
                    console.print(f"  [red]✗[/] {v['type']} (Vote #{v.get('vote_id', 'N/A')}): {v}")
                sys.exit(1)
        finally:
            await engine.close()
            
    asyncio.run(_ledger_verify_async())

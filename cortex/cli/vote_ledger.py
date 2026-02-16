"""CLI commands: vote, ledger verify, ledger checkpoint."""

from __future__ import annotations

import sys

import click
from rich.panel import Panel

from cortex.cli import cli, console, get_engine, DEFAULT_DB


@cli.command()
@click.argument("fact_id", type=int)
@click.argument("value", type=int)
@click.option("--agent", "-a", default="human", help="Agent name")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def vote(fact_id, value, agent, db) -> None:
    """Cast a consensus vote on a fact (1=verify, -1=dispute)."""
    engine = get_engine(db)
    try:
        if value not in [1, -1]:
            console.print("[red]✗ Vote must be 1 (verify) or -1 (dispute)[/]")
            return
        score = engine.vote(fact_id, agent, value)
        color = "green" if score >= 1.0 else "red"
        console.print(
            f"[green]✓[/] Agent [bold]{agent}[/] voted {value} on fact [bold]#{fact_id}[/]. "
            f"New score: [{color}]{score:.2f}[/]"
        )
    finally:
        engine.close()


@cli.group()
def ledger():
    """Manage the immutable transaction ledger."""
    pass


@ledger.command("verify")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def ledger_verify(db):
    """Verify cryptographic integrity of the ledger."""
    from cortex.ledger import ImmutableLedger
    engine = get_engine(db)
    try:
        _ledger = ImmutableLedger(engine.get_connection())
        with console.status("[bold blue]Verifying ledger integrity...[/]"):
            report = _ledger.verify_integrity()
        if report["valid"]:
            console.print(Panel(
                f"[bold green]✅ Ledger Integrity: OK[/]\n"
                f"Transactions checked: {report['tx_checked']}\n"
                f"Merkle roots checked: {report['roots_checked']}",
                title="🔐 Immutable Ledger", border_style="green",
            ))
        else:
            console.print(Panel(
                f"[bold red]❌ Ledger Integrity: VIOLATION DETECTED[/]\n"
                f"Violations found: {len(report['violations'])}",
                title="🔐 Immutable Ledger", border_style="red",
            ))
            for v in report["violations"]:
                console.print(f"  [red]✗[/] {v['type']} (TX #{v.get('tx_id', 'N/A')}): {v}")
            sys.exit(1)
    finally:
        engine.close()


@ledger.command("checkpoint")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def ledger_checkpoint(db):
    """Create a new Merkle tree checkpoint for recent transactions."""
    from cortex.ledger import ImmutableLedger
    engine = get_engine(db)
    try:
        _ledger = ImmutableLedger(engine.get_connection())
        with console.status("[bold blue]Creating checkpoint...[/]"):
            checkpoint_id = _ledger.create_checkpoint()
        if checkpoint_id:
            console.print(f"[green]✓[/] Created Merkle checkpoint [bold]#{checkpoint_id}[/]")
        else:
            console.print("[yellow]! Not enough transactions for a new checkpoint.[/]")
    finally:
        engine.close()

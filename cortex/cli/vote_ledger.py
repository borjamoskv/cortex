"""Comandos de CLI: vote, ledger verify, ledger checkpoint."""

from __future__ import annotations

import asyncio
import sys

import click
from rich.panel import Panel

from cortex.cli import DEFAULT_DB, cli, console, get_engine

# Importe actualizado para Wave 5 Fase 2
from cortex.consensus.vote_ledger import ImmutableVoteLedger


@cli.command()
@click.argument("fact_id", type=int)
@click.argument("value", type=int)
@click.option("--agent", "-a", default="human", help="Nombre del agente")
@click.option("--db", default=DEFAULT_DB, help="Ruta de la base de datos")
def vote(fact_id, value, agent, db) -> None:
    """Emite un voto de consenso sobre un hecho (1=verificar, -1=disputar)."""

    async def _vote_async():
        engine = get_engine(db)
        try:
            # En Wave 5 usamos sesiones transaccionales
            async with engine.session() as conn:
                ledger = ImmutableVoteLedger(engine._pool if hasattr(engine, "_pool") else conn)

                if value not in [1, -1]:
                    console.print("[red]✗ El voto debe ser 1 (verificar) o -1 (disputar)[/]")
                    return

                # Peso 10.0 para votos humanos
                entry = await ledger.append_vote(fact_id, agent, value, 10.0)
                await conn.commit()

                console.print(
                    f"[green]✓[/] El agente [bold]{agent}[/] votó {value} en el hecho [bold]#{fact_id}[/].\n"
                    f"   [dim]Hash: {entry.hash[:16]}...[/]"
                )
        finally:
            await engine.close()

    asyncio.run(_vote_async())


@cli.group()
def ledger():
    """Administrar el registro inmutable de votos."""
    pass


@ledger.command("status")
@click.option("--db", default=DEFAULT_DB, help="Ruta de la base de datos")
def ledger_status(db):
    """Muestra el estado actual del registro de votos."""

    async def _ledger_status_async():
        engine = get_engine(db)
        try:
            async with engine.session() as conn:
                async with conn.execute("SELECT COUNT(*) FROM vote_ledger") as cursor:
                    vote_count = (await cursor.fetchone())[0]
                async with conn.execute("SELECT COUNT(*) FROM vote_merkle_roots") as cursor:
                    checkpoint_count = (await cursor.fetchone())[0]
                async with conn.execute("SELECT MAX(vote_end_id) FROM vote_merkle_roots") as cursor:
                    last_audited = (await cursor.fetchone())[0] or 0

                console.print(
                    Panel(
                        f"[bold cyan]Altura del Registro:[/] {vote_count} votos\n"
                        f"[bold cyan]Puntos de Control:[/] {checkpoint_count}\n"
                        f"[bold cyan]Último ID Auditado:[/] {last_audited}\n"
                        f"[bold cyan]Votos no Auditados:[/] {vote_count - last_audited}",
                        title="📊 Estado del Registro de Votos",
                        border_style="cyan",
                    )
                )
        finally:
            await engine.close()

    asyncio.run(_ledger_status_async())


@ledger.command("checkpoint")
@click.option("--db", default=DEFAULT_DB, help="Ruta de la base de datos")
def ledger_checkpoint(db):
    """Activa manualmente un punto de control (Merkle root)."""

    async def _ledger_checkpoint_async():
        engine = get_engine(db)
        try:
            async with engine.session() as conn:
                ledger = ImmutableVoteLedger(engine._pool if hasattr(engine, "_pool") else conn)
                with console.status(
                    "[bold yellow]Calculando Merkle Root y creando punto de control...[/]"
                ):
                    root = await ledger.create_checkpoint()

                if root:
                    console.print(
                        f"[green]✅ Punto de control creado con éxito.[/] Raíz: [bold]{root}[/]"
                    )
                else:
                    console.print("[yellow]⚠ No hay votos nuevos para auditar.[/]")
        finally:
            await engine.close()

    asyncio.run(_ledger_checkpoint_async())


@ledger.command("verify")
@click.option("--db", default=DEFAULT_DB, help="Ruta de la base de datos")
def ledger_verify(db):
    """Verifica la integridad criptográfica del registro de votos."""

    async def _ledger_verify_async():
        engine = get_engine(db)
        try:
            async with engine.session() as conn:
                ledger = ImmutableVoteLedger(engine._pool if hasattr(engine, "_pool") else conn)
                with console.status(
                    "[bold blue]Verificando la cadena de hashes del registro...[/]"
                ):
                    report = await ledger.verify_chain_integrity()

                with console.status("[bold magenta]Verificando raíces de Merkle...[/]"):
                    merkle_report = await ledger.verify_merkle_roots()

                chain_valid = report["valid"]
                merkle_valid = all(r["valid"] for r in merkle_report)

                if chain_valid:
                    console.print(
                        f"[green]✅ Integridad de Cadena de Hashes: OK[/] ({report['votes_checked']} votos)"
                    )
                else:
                    console.print("[red]❌ Integridad de Cadena de Hashes: FALLIDA[/]")
                    for v in report["violations"]:
                        console.print(
                            f"  [red]✗[/] {v['type']} en el Voto #{v.get('vote_id', 'N/A')}"
                        )

                if merkle_valid:
                    console.print(
                        f"[green]✅ Integridad de Raíz Merkle: OK[/] ({len(merkle_report)} puntos de control)"
                    )
                else:
                    console.print("[red]❌ Integridad de Raíz Merkle: FALLIDA[/]")
                    for r in merkle_report:
                        if not r["valid"]:
                            console.print(
                                f"  [red]✗[/] ¡Desajuste en Punto de Control {r['checkpoint_id']}! Esperado {r['expected'][:16]}... vs Actual {r['actual'][:16]}..."
                            )

                if not (chain_valid and merkle_valid):
                    sys.exit(1)
        finally:
            await engine.close()

    asyncio.run(_ledger_verify_async())

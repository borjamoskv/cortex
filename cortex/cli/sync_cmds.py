"""CLI commands: sync, export, writeback."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.panel import Panel

from cortex.cli import DEFAULT_DB, cli, console, get_engine
from cortex.sync import export_obsidian, export_snapshot, export_to_json, sync_memory


def _run_async(coro):
    """Helper to run async coroutines from sync CLI."""
    return asyncio.run(coro)


@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
def sync(db) -> None:
    """Sincronizar ~/.agent/memory/ → CORTEX (incremental)."""
    engine = get_engine(db)
    engine.init_db_sync()
    try:
        with console.status("[bold blue]Sincronizando memoria...[/]"):
            # Fix: Wrap async call
            result = _run_async(sync_memory(engine))

        if result.had_changes:
            console.print(
                Panel(
                    f"[bold green]✓ Sincronización completada[/]\n"
                    f"Facts: {result.facts_synced}\n"
                    f"Ghosts: {result.ghosts_synced}\n"
                    f"Errores: {result.errors_synced}\n"
                    f"Bridges: {result.bridges_synced}\n"
                    f"Omitidos (ya existían): {result.skipped}",
                    title="🔄 CORTEX Sync",
                    border_style="green",
                )
            )
        else:
            console.print("[dim]Sin cambios desde la última sincronización.[/]")
        if result.errors:
            for err in result.errors:
                console.print(f"[red]  ✗ {err}[/]")
    finally:
        # Fix: engine.close is async
        _run_async(engine.close())


@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--out", default="~/.cortex/context-snapshot.md", help="Ruta de salida")
def export(db, out) -> None:
    """Exportar snapshot de CORTEX a markdown (para lectura automática del agente)."""
    engine = get_engine(db)
    engine.init_db_sync()
    try:
        out_path = Path(out).expanduser()
        # Fix: Wrap async call
        _run_async(export_snapshot(engine, out_path))
        console.print(f"[green]✓[/] Snapshot exportado a [cyan]{out_path}[/]")
    finally:
        # Fix: engine.close is async
        _run_async(engine.close())


@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
def writeback(db) -> None:
    """Write-back: CORTEX DB → ~/.agent/memory/ (DB es Source of Truth)."""
    engine = get_engine(db)
    try:
        result = export_to_json(engine)
        if result.had_changes:
            console.print(
                Panel(
                    f"[bold green]✓ Write-back completado[/]\n"
                    f"Archivos actualizados: {result.files_written}\n"
                    f"Archivos sin cambios: {result.files_skipped}\n"
                    f"Items exportados: {result.items_exported}",
                    title="🔄 CORTEX → JSON",
                    border_style="cyan",
                )
            )
        else:
            console.print(
                "[dim]Sin cambios en DB desde el último write-back. "
                f"({result.files_skipped} archivos verificados)[/]"
            )
        for err in result.errors:
            console.print(f"[red]  ✗ {err}[/]")
    finally:
        # Fix: engine.close is async
        _run_async(engine.close())


@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option(
    "--out",
    default="~/.cortex/obsidian-vault",
    help="Ruta del vault Obsidian de salida",
)
def obsidian(db, out) -> None:
    """Exportar CORTEX como vault de Obsidian con notas interconectadas."""
    engine = get_engine(db)
    engine.init_db_sync()
    try:
        out_path = Path(out).expanduser()
        with console.status("[bold blue]Generando vault Obsidian...[/]"):
            stats = _run_async(export_obsidian(engine, out_path))

        console.print(
            Panel(
                f"[bold green]✓ Vault Obsidian generado[/]\n"
                f"Notas creadas: {stats['notes_created']}\n"
                f"Facts exportados: {stats['total_facts']}\n"
                f"Proyectos: {', '.join(stats['projects'])}\n"
                f"Tags: {len(stats['tags'])}\n"
                f"Ruta: {stats['vault_path']}",
                title="📓 CORTEX → Obsidian",
                border_style="magenta",
            )
        )
    finally:
        _run_async(engine.close())

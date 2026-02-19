"""CLI commands: delete, list, edit."""

from __future__ import annotations

import json

import click
from rich.table import Table

from cortex.cli import DEFAULT_DB, cli, console, get_engine
from cortex.sync import export_to_json


@cli.command()
@click.argument("fact_id", type=int)
@click.option("--reason", "-r", default=None, help="Razón de la eliminación")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def delete(fact_id, reason, db) -> None:
    """Soft-delete: depreca un fact y auto-sincroniza JSON."""
    engine = get_engine(db)
    try:
        conn = engine._get_sync_conn()
        row = conn.execute(
            "SELECT project, content, fact_type FROM facts WHERE id = ? AND valid_until IS NULL",
            (fact_id,),
        ).fetchone()
        if not row:
            console.print(f"[red]✗ No se encontró fact activo con ID {fact_id}[/]")
            return
        console.print(
            f"[dim]Deprecando:[/] [bold]#{fact_id}[/] "
            f"[cyan]{row[0]}[/] ({row[2]}) — {row[1][:80]}..."
        )
        success = engine.deprecate_sync(fact_id, reason or "deleted-via-cli")
        if success:
            wb = export_to_json(engine)
            console.print(
                f"[green]✓[/] Fact #{fact_id} deprecado. "
                f"Write-back: {wb.files_written} archivos actualizados."
            )
        else:
            console.print(f"[red]✗ No se pudo deprecar fact #{fact_id}[/]")
    finally:
        engine.close()


@cli.command("list")
@click.option("--project", "-p", default=None, help="Filtrar por proyecto")
@click.option("--type", "fact_type", default=None, help="Filtrar por tipo")
@click.option("--limit", "-n", default=20, help="Máximo de resultados")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def list_facts(project, fact_type, limit, db) -> None:
    """Listar facts activos (tabulado)."""
    engine = get_engine(db)
    try:
        conn = engine._get_sync_conn()
        query = """
            SELECT id, project, content, fact_type, tags, created_at
            FROM facts WHERE valid_until IS NULL
        """
        params = []
        if project:
            query += " AND project = ?"
            params.append(project)
        if fact_type:
            query += " AND fact_type = ?"
            params.append(fact_type)
        query += " ORDER BY project, fact_type, id"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        rows = conn.execute(query, params).fetchall()
        if not rows:
            console.print("[dim]No se encontraron facts activos.[/]")
            return
        table = Table(title=f"CORTEX Facts ({len(rows)})", border_style="cyan")
        table.add_column("ID", style="bold", width=5)
        table.add_column("Proyecto", style="cyan", width=18)
        table.add_column("Tipo", width=10)
        table.add_column("Contenido", width=60)
        table.add_column("Tags", style="dim", width=15)
        for row in rows:
            content_preview = row[2][:57] + "..." if len(row[2]) > 60 else row[2]
            tags = json.loads(row[4]) if row[4] else []
            tags_str = ", ".join(tags[:2]) + ("…" if len(tags) > 2 else "")
            table.add_row(str(row[0]), row[1], row[3], content_preview, tags_str)
        console.print(table)
    finally:
        engine.close()


@cli.command()
@click.argument("fact_id", type=int)
@click.argument("new_content")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def edit(fact_id, new_content, db) -> None:
    """Editar un fact: depreca el viejo y crea uno nuevo con el contenido actualizado."""
    engine = get_engine(db)
    try:
        conn = engine._get_sync_conn()
        row = conn.execute(
            "SELECT project, content, fact_type, tags, confidence, source FROM facts "
            "WHERE id = ? AND valid_until IS NULL",
            (fact_id,),
        ).fetchone()
        if not row:
            console.print(f"[red]✗ No se encontró fact activo con ID {fact_id}[/]")
            return
        project, old_content, fact_type, tags_json, confidence, source = row
        try:
            tags = json.loads(tags_json) if tags_json else None
        except (json.JSONDecodeError, TypeError):
            tags = None
        engine.deprecate_sync(fact_id, "edited → new version")
        new_id = engine.store_sync(
            project=project,
            content=new_content,
            fact_type=fact_type,
            tags=tags,
            confidence=confidence,
            source=source or "edit-via-cli",
        )
        wb = export_to_json(engine)
        console.print(
            f"[green]✓[/] Fact #{fact_id} → #{new_id} editado.\n"
            f"  [dim]Antes:[/] {old_content[:60]}...\n"
            f"  [bold]Ahora:[/] {new_content[:60]}...\n"
            f"  Write-back: {wb.files_written} archivos actualizados."
        )
    finally:
        engine.close()

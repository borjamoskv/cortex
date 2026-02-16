"""
CORTEX v4.0 — CLI Interface.

Command-line tool for the sovereign memory engine.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import os
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex import __version__
from cortex.engine import CortexEngine
from cortex.sync import export_snapshot, export_to_json, sync_memory
from cortex.timing import TimingTracker

console = Console()
from cortex.config import DEFAULT_DB_PATH
from cortex.launchpad import MissionOrchestrator
DEFAULT_DB = str(DEFAULT_DB_PATH)


def get_engine(db: str = DEFAULT_DB) -> CortexEngine:
    """Create an engine instance."""
    return CortexEngine(db_path=db)


def get_tracker(engine: CortexEngine) -> TimingTracker:
    """Create a timing tracker from an engine."""
    return TimingTracker(engine._get_conn())


# ─── Main Group ──────────────────────────────────────────────────

@click.group()
@click.version_option(__version__, prog_name="cortex")
def cli() -> None:
    """CORTEX — The Sovereign Ledger for AI Agents."""
    pass


# ─── Init ────────────────────────────────────────────────────────

@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
def init(db) -> None:
    """Initialize CORTEX database."""
    engine = get_engine(db)
    try:
        engine.init_db()
        console.print(Panel(
            f"[bold green]✓ CORTEX v{__version__} initialized[/]\n"
            f"Database: {engine._db_path}",
            title="🧠 CORTEX",
            border_style="green",
        ))
    finally:
        engine.close()


# ─── Store ───────────────────────────────────────────────────────

@cli.command()
@click.argument("project")
@click.argument("content")
@click.option("--type", "fact_type", default="knowledge", help="Fact type")
@click.option("--tags", default=None, help="Comma-separated tags")
@click.option("--confidence", default="stated", help="Confidence level")
@click.option("--source", default=None, help="Source of the fact")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def store(project, content, fact_type, tags, confidence, source, db) -> None:
    """Store a fact in CORTEX."""
    engine = get_engine(db)
    try:
        tag_list = [t.strip() for t in tags.split(",")] if tags else None

        fact_id = engine.store(
            project=project,
            content=content,
            fact_type=fact_type,
            tags=tag_list,
            confidence=confidence,
            source=source,
        )

        console.print(f"[green]✓[/] Stored fact [bold]#{fact_id}[/] in [cyan]{project}[/]")
    finally:
        engine.close()


# ─── Search ──────────────────────────────────────────────────────

@cli.command()
@click.argument("query")
@click.option("--project", "-p", default=None, help="Scope to project")
@click.option("--top", "-k", default=5, help="Number of results")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def search(query, project, top, db) -> None:
    """Semantic search across CORTEX memory."""
    engine = get_engine(db)
    try:
        with console.status("[bold blue]Searching...[/]"):
            results = engine.search(query, project=project, top_k=top)

        if not results:
            console.print("[yellow]No results found.[/]")
            return

        table = Table(title=f"🔍 Results for: '{query}'")
        table.add_column("#", style="dim", width=4)
        table.add_column("Project", style="cyan", width=15)
        table.add_column("Content", width=50)
        table.add_column("Type", style="magenta", width=10)
        table.add_column("Score", style="green", width=6)

        for r in results:
            content = r.content[:80] + "..." if len(r.content) > 80 else r.content
            table.add_row(
                str(r.fact_id),
                r.project,
                content,
                r.fact_type,
                f"{r.score:.2f}",
            )

        console.print(table)
    finally:
        engine.close()


# ─── Recall ──────────────────────────────────────────────────────

@cli.command()
@click.argument("project")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def recall(project, db) -> None:
    """Load full context for a project."""
    engine = get_engine(db)
    try:
        facts = engine.recall(project)

        if not facts:
            console.print(f"[yellow]No facts found for project '{project}'[/]")
            return

        console.print(Panel(
            f"[bold]{project}[/] — {len(facts)} active facts",
            title="🧠 CORTEX Recall",
            border_style="cyan",
        ))

        # Group by type
        by_type: dict[str, list] = {}
        for f in facts:
            by_type.setdefault(f.fact_type, []).append(f)

        for ftype, type_facts in by_type.items():
            console.print(f"\n[bold magenta]═══ {ftype.upper()} ({len(type_facts)}) ═══[/]")
            for f in type_facts:
                tags_str = f" [dim]{', '.join(f.tags)}[/]" if f.tags else ""
                console.print(f"  [dim]#{f.id}[/] {f.content}{tags_str}")
    finally:
        engine.close()


# ─── History ─────────────────────────────────────────────────────

@cli.command()
@click.argument("project")
@click.option("--at", "as_of", default=None, help="Point-in-time (ISO 8601)")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def history(project, as_of, db) -> None:
    """Temporal query: what did we know at a specific time?"""
    engine = get_engine(db)
    try:
        facts = engine.history(project, as_of=as_of)

        label = f"as of {as_of}" if as_of else "all time"
        console.print(Panel(
            f"[bold]{project}[/] — {len(facts)} facts ({label})",
            title="⏰ CORTEX History",
            border_style="yellow",
        ))

        for f in facts:
            status = "[green]●[/]" if f.is_active() else "[red]○[/]"
            console.print(
                f"  {status} [dim]#{f.id}[/] [{f.valid_from[:10]}] {f.content[:80]}"
            )
    finally:
        engine.close()


# ─── Status ──────────────────────────────────────────────────────

@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def status(db, json_output) -> None:
    """Show CORTEX health and statistics."""
    engine = get_engine(db)
    try:
        try:
            s = engine.stats()
        except (sqlite3.OperationalError, FileNotFoundError) as e:
            console.print(f"[red]Error: {e}[/]")
            console.print("[dim]Run 'cortex init' first.[/]")
            return

        if json_output:
            click.echo(json.dumps(s, indent=2))
            return

        table = Table(title="🧠 CORTEX Status")
        table.add_column("Metric", style="bold")
        table.add_column("Value", style="cyan")

        table.add_row("Version", __version__)
        table.add_row("Database", s["db_path"])
        table.add_row("Size", f"{s['db_size_mb']} MB")
        table.add_row("Total Facts", str(s["total_facts"]))
        table.add_row("Active Facts", f"[green]{s['active_facts']}[/]")
        table.add_row("Deprecated", f"[dim]{s['deprecated_facts']}[/]")
        table.add_row("Projects", str(s["project_count"]))
        table.add_row("Embeddings", str(s["embeddings"]))
        table.add_row("Transactions", str(s["transactions"]))

        if s["types"]:
            types_str = ", ".join(f"{t}: {c}" for t, c in s["types"].items())
            table.add_row("By Type", types_str)

        console.print(table)
    finally:
        engine.close()


# ─── Migrate ─────────────────────────────────────────────────────

@cli.command()
@click.option("--source", default="~/.agent/memory", help="v3.1 memory directory")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def migrate(source, db) -> None:
    """Import CORTEX v3.1 data into v4.0."""
    from cortex.migrate import migrate_v31_to_v40

    engine = get_engine(db)
    engine.init_db()

    try:
        with console.status("[bold blue]Migrating v3.1 → v4.0...[/]"):
            stats = migrate_v31_to_v40(engine, source)

        console.print(Panel(
            f"[bold green]✓ Migration complete![/]\n"
            f"Facts imported: {stats['facts_imported']}\n"
            f"Errors imported: {stats['errors_imported']}\n"
            f"Bridges imported: {stats['bridges_imported']}\n"
            f"Sessions imported: {stats['sessions_imported']}",
            title="🔄 v3.1 → v4.0 Migration",
            border_style="green",
        ))
    finally:
        engine.close()


@cli.command("migrate-graph")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def migrate_graph(db) -> None:
    """Migrate local SQLite graph data to Neo4j global knowledge graph."""
    engine = get_engine(db)
    try:
        from cortex.graph import process_fact_graph, GRAPH_BACKEND
        
        if GRAPH_BACKEND != "neo4j":
            console.print("[yellow]WARNING: CORTEX_GRAPH_BACKEND is not set to 'neo4j'.[/]")
            console.print("[dim]Migration will only re-process data into SQLite unless you set CORTEX_GRAPH_BACKEND=neo4j.[/]")
            if not click.confirm("Do you want to continue?", default=False):
                return

        conn = engine._get_conn()
        # Fetch all facts that don't have relationships yet (best effort)
        # or just fetch all and let deduplication handle it.
        facts = conn.execute("SELECT id, content, project, created_at FROM facts").fetchall()
        
        console.print(f"[bold blue]Migrating {len(facts)} facts to Graph Memory...[/]")
        
        processed = 0
        with console.status("[bold blue]Processing...[/]") as status:
            for fid, content, project, ts in facts:
                try:
                    process_fact_graph(conn, fid, content, project, ts)
                    processed += 1
                    if processed % 10 == 0:
                        status.update(f"[bold blue]Processed {processed}/{len(facts)}...[/]")
                except Exception as e:
                    console.print(f"[red]✗ Failed at fact #{fid}: {e}[/]")

        console.print(Panel(
            f"[bold green]✓ Graph Migration Complete![/]\n"
            f"Facts processed: {processed}\n"
            f"Backend: {GRAPH_BACKEND}",
            title="🧠 Graph Migration",
            border_style="green",
        ))
    finally:
        engine.close()


# ─── Sync ────────────────────────────────────────────────────────

@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
def sync(db) -> None:
    """Sincronizar ~/.agent/memory/ → CORTEX (incremental)."""


    engine = get_engine(db)
    engine.init_db()

    try:
        with console.status("[bold blue]Sincronizando memoria...[/]"):
            result = sync_memory(engine)

        if result.had_changes:
            console.print(Panel(
                f"[bold green]✓ Sincronización completada[/]\n"
                f"Facts: {result.facts_synced}\n"
                f"Ghosts: {result.ghosts_synced}\n"
                f"Errores: {result.errors_synced}\n"
                f"Bridges: {result.bridges_synced}\n"
                f"Omitidos (ya existían): {result.skipped}",
                title="🔄 CORTEX Sync",
                border_style="green",
            ))
        else:
            console.print("[dim]Sin cambios desde la última sincronización.[/]")

        if result.errors:
            for err in result.errors:
                console.print(f"[red]  ✗ {err}[/]")

    finally:
        engine.close()


# ─── Export ──────────────────────────────────────────────────────

@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--out", default="~/.cortex/context-snapshot.md", help="Ruta de salida")
def export(db, out) -> None:
    """Exportar snapshot de CORTEX a markdown (para lectura automática del agente)."""


    engine = get_engine(db)
    try:
        out_path = Path(out).expanduser()
        export_snapshot(engine, out_path)
        console.print(f"[green]✓[/] Snapshot exportado a [cyan]{out_path}[/]")
    finally:
        engine.close()


@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
def writeback(db) -> None:
    """Write-back: CORTEX DB → ~/.agent/memory/ (DB es Source of Truth)."""


    engine = get_engine(db)
    try:
        result = export_to_json(engine)

        if result.had_changes:
            console.print(Panel(
                f"[bold green]✓ Write-back completado[/]\n"
                f"Archivos actualizados: {result.files_written}\n"
                f"Archivos sin cambios: {result.files_skipped}\n"
                f"Items exportados: {result.items_exported}",
                title="🔄 CORTEX → JSON",
                border_style="cyan",
            ))
        else:
            console.print(
                "[dim]Sin cambios en DB desde el último write-back. "
                f"({result.files_skipped} archivos verificados)[/]"
            )

        for err in result.errors:
            console.print(f"[red]  ✗ {err}[/]")

    finally:
        engine.close()


# ─── Delete (Soft-Delete + Auto Write-back) ──────────────────────

@cli.command()
@click.argument("fact_id", type=int)
@click.option("--reason", "-r", default=None, help="Razón de la eliminación")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def delete(fact_id, reason, db) -> None:
    """Soft-delete: depreca un fact y auto-sincroniza JSON."""
    engine = get_engine(db)
    try:
        conn = engine.get_connection()

        # Mostrar qué se va a borrar
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

        success = engine.deprecate(fact_id, reason or "deleted-via-cli")

        if success:
            # Auto write-back (Closed Loop)

            wb = export_to_json(engine)
            console.print(
                f"[green]✓[/] Fact #{fact_id} deprecado. "
                f"Write-back: {wb.files_written} archivos actualizados."
            )
        else:
            console.print(f"[red]✗ No se pudo deprecar fact #{fact_id}[/]")

    finally:
        engine.close()


# ─── List (Read) ─────────────────────────────────────────────────

@cli.command("list")
@click.option("--project", "-p", default=None, help="Filtrar por proyecto")
@click.option("--type", "fact_type", default=None, help="Filtrar por tipo")
@click.option("--limit", "-n", default=20, help="Máximo de resultados")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def list_facts(project, fact_type, limit, db) -> None:
    """Listar facts activos (tabulado)."""
    engine = get_engine(db)
    try:
        conn = engine.get_connection()

        query = """
            SELECT id, project, content, fact_type, tags, created_at
            FROM facts
            WHERE valid_until IS NULL
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


# ─── Edit (Deprecate + Store + Auto Write-back) ─────────────────

@cli.command()
@click.argument("fact_id", type=int)
@click.argument("new_content")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def edit(fact_id, new_content, db) -> None:
    """Editar un fact: depreca el viejo y crea uno nuevo con el contenido actualizado."""
    engine = get_engine(db)
    try:
        conn = engine.get_connection()

        # Obtener fact original
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

        # Deprecar el viejo
        engine.deprecate(fact_id, f"edited → new version")

        # Crear el nuevo con los mismos metadatos
        new_id = engine.store(
            project=project,
            content=new_content,
            fact_type=fact_type,
            tags=tags,
            confidence=confidence,
            source=source or "edit-via-cli",
        )

        # Auto write-back
        wb = export_to_json(engine)

        console.print(
            f"[green]✓[/] Fact #{fact_id} → #{new_id} editado.\n"
            f"  [dim]Antes:[/] {old_content[:60]}...\n"
            f"  [bold]Ahora:[/] {new_content[:60]}...\n"
            f"  Write-back: {wb.files_written} archivos actualizados."
        )
    finally:
        engine.close()


# ─── Time Tracking ───────────────────────────────────────────────

@cli.command("time")
@click.option("--project", "-p", default=None, help="Filter by project")
@click.option("--days", "-d", default=1, help="Number of days (default: 1 = today)")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def time_cmd(project, days, db) -> None:
    """Show time tracking summary."""
    engine = get_engine(db)
    try:
        engine.init_db()
        t = get_tracker(engine)

        if days <= 1:
            summary = t.today(project=project)
            title = "⏱ Today's Time"
        else:
            summary = t.report(project=project, days=days)
            title = f"⏱ Last {days} Days"

        if summary.total_seconds == 0:
            console.print("[yellow]No time tracked yet.[/]")
            return

        table = Table(title=title)
        table.add_column("Metric", style="bold")
        table.add_column("Value", style="cyan")

        table.add_row("Total", summary.format_duration(summary.total_seconds))
        table.add_row("Entries", str(summary.entries))
        table.add_row("Heartbeats", str(summary.heartbeats))

        if summary.by_category:
            for cat, secs in sorted(summary.by_category.items(), key=lambda x: -x[1]):
                table.add_row(f"  {cat}", summary.format_duration(secs))

        if summary.by_project:
            table.add_row("", "")
            for proj, secs in sorted(summary.by_project.items(), key=lambda x: -x[1]):
                table.add_row(f"  📁 {proj}", summary.format_duration(secs))

        if summary.top_entities:
            table.add_row("", "")
            for entity, count in summary.top_entities[:5]:
                table.add_row(f"  📄 {entity}", f"{count} hits")

        console.print(table)
    finally:
        engine.close()


@cli.command("heartbeat")
@click.argument("project")
@click.argument("entity", default="")
@click.option("--category", "-c", default=None, help="Activity category")
@click.option("--branch", "-b", default=None, help="Git branch")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def heartbeat_cmd(project, entity, category, branch, db) -> None:
    """Record an activity heartbeat."""
    engine = get_engine(db)
    try:
        engine.init_db()
        t = get_tracker(engine)

        hb_id = t.heartbeat(
            project=project,
            entity=entity,
            category=category,
            branch=branch,
        )
        t.flush()

        console.print(f"[green]✓[/] Heartbeat [bold]#{hb_id}[/] → [cyan]{project}[/]/{entity}")
    finally:
        engine.close()


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
        console.print(f"[green]✓[/] Agent [bold]{agent}[/] voted {value} on fact [bold]#{fact_id}[/]. "
                      f"New score: [{color}]{score:.2f}[/]")
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
                title="🔐 Immutable Ledger",
                border_style="green",
            ))
        else:
            console.print(Panel(
                f"[bold red]❌ Ledger Integrity: VIOLATION DETECTED[/]\n"
                f"Violations found: {len(report['violations'])}",
                title="🔐 Immutable Ledger",
                border_style="red",
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


@cli.group()
def timeline():
    """Navigate the CORTEX timeline and manage snapshots."""
    pass


@timeline.command("log")
@click.option("--limit", "-n", default=20, help="Number of transactions")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def timeline_log(limit, db):
    """Show the transaction history ledger."""
    engine = get_engine(db)
    try:
        conn = engine.get_connection()
        rows = conn.execute(
            "SELECT id, project, action, hash, timestamp FROM transactions ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()

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
            table.add_row(
                f"#{row[0]}",
                row[1],
                row[2],
                row[3][:12] + "...",
                row[4]
            )
        console.print(table)
    finally:
        engine.close()


@timeline.command("checkout")
@click.argument("tx_id", type=int)
@click.option("--project", "-p", default=None, help="Filter by project")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def timeline_checkout(tx_id, project, db):
    """Reconstruct state at a specific transaction ID."""
    engine = get_engine(db)
    try:
        with console.status(f"[bold blue]Reconstructing state at TX #{tx_id}...[/]"):
            facts = engine.reconstruct_state(tx_id, project=project)

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
                str(f.id),
                f.project,
                f.fact_type,
                f.content[:50] + "..." if len(f.content) > 50 else f.content,
                f"{f.consensus_score:.2f}"
            )
        console.print(table)
    finally:
        engine.close()


@timeline.group("snapshot")
def timeline_snapshot():
    """Manage physical database snapshots."""
    pass


@timeline_snapshot.command("create")
@click.argument("name")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def snapshot_create(name, db):
    """Create a new physical snapshot."""
    from cortex.snapshots import SnapshotManager
    from cortex.ledger import ImmutableLedger
    
    engine = get_engine(db)
    try:
        conn = engine.get_connection()
        
        # Get latest TX and Merkle Root for metadata
        ledger = ImmutableLedger(conn)
        latest_tx = conn.execute("SELECT id FROM transactions ORDER BY id DESC LIMIT 1").fetchone()
        tx_id = latest_tx[0] if latest_tx else 0
        
        # Best effort: get latest merkle root
        root_row = conn.execute("SELECT root_hash FROM merkle_roots ORDER BY id DESC LIMIT 1").fetchone()
        merkle_root = root_row[0] if root_row else "0xGENESIS"
        
        sm = SnapshotManager(db_path=db)
        with console.status("[bold blue]Creating physical snapshot...[/]"):
            snap = sm.create_snapshot(name, tx_id, merkle_root)
            
        console.print(f"[green]✓[/] Snapshot [bold]'{name}'[/] created successfully.")
        console.print(f"  [dim]Path:[/] {snap.path}")
        console.print(f"  [dim]TX ID:[/] {snap.tx_id}")
        console.print(f"  [dim]Size:[/] {snap.size_mb} MB")
    finally:
        engine.close()


@timeline_snapshot.command("list")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def snapshot_list(db):
    """List all available snapshots."""
    from cortex.snapshots import SnapshotManager
    sm = SnapshotManager(db_path=db)
    snaps = sm.list_snapshots()
    
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
            s.name,
            str(s.tx_id),
            s.created_at[:19].replace("T", " "),
            f"{s.size_mb} MB"
        )
    console.print(table)


# ─── Launchpad ───────────────────────────────────────────────────

@cli.group()
def launchpad():
    """Orchestrate AI Swarm missions via CORTEX Launchpad."""
    pass


@launchpad.command("launch")
@click.argument("project")
@click.argument("goal", required=False)
@click.option("--file", "-f", "mission_file", type=click.Path(exists=True), help="YAML/JSON mission definition file")
@click.option("--formation", default="IRON_DOME", help="Swarm formation")
@click.option("--agents", "-a", default=10, help="Number of agents")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def mission_launch(project, goal, mission_file, formation, agents, db):
    """Launch a new swarm mission. Provide a goal or a mission file."""
    if not goal and not mission_file:
        console.print("[red]Error: You must provide either a goal or a mission file (--file).[/]")
        return

    engine = get_engine(db)
    orchestrator = MissionOrchestrator(engine)
    
    try:
        display_goal = goal if goal else f"File: {os.path.basename(mission_file)}"
        with console.status(f"[bold blue]Launching mission in {project}: {display_goal}...[/]"):
            result = orchestrator.launch(
                project=project,
                goal=goal,
                formation=formation,
                agents=agents,
                mission_file=mission_file
            )
            
        if result["status"] == "success":
            console.print(Panel(
                f"[bold green]✓ Mission Launched Successfully[/]\n"
                f"Intent ID: [cyan]#{result['intent_id']}[/]\n"
                f"Result ID: [cyan]#{result['result_id']}[/]\n"
                f"Status: {result['status'].upper()}",
                title="🐝 Mission Control",
                border_style="green",
            ))
            # Show snippet of output
            console.print(f"\n[dim]Recent Output:[/]\n{result['stdout'][-500:]}")
        else:
            console.print(Panel(
                f"[bold red]✗ Mission Failed[/]\n"
                f"Intent ID: {result.get('intent_id', 'N/A')}\n"
                f"Error: {result.get('error', 'Check stderr')}",
                title="🐝 Mission Control",
                border_style="red",
            ))
            if "stderr" in result:
                console.print(f"\n[red]Stderr:[/]\n{result['stderr']}")
                
    finally:
        engine.close()


@launchpad.command("list")
@click.option("--project", "-p", default=None, help="Filter by project")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def mission_list(project, db):
    """List recent swarm missions from the ledger."""
    engine = get_engine(db)
    orchestrator = MissionOrchestrator(engine)
    try:
        missions = orchestrator.list_missions(project=project)
        
        if not missions:
            console.print("[yellow]No missions found in the ledger.[/]")
            return
            
        table = Table(title="🐝 Swarm Mission History")
        table.add_column("ID", style="bold", width=6)
        table.add_column("Project", style="cyan", width=15)
        table.add_column("Type", width=10)
        table.add_column("Description", width=50)
        table.add_column("Created At", width=20)
        
        for m in missions:
            table.add_row(
                str(m["id"]),
                m["project"],
                m["fact_type"],
                m["content"][:50] + "...",
                m["created_at"]
            )
        console.print(table)
    finally:
        engine.close()


# ─── MEJORAlo ────────────────────────────────────────────────────

@cli.group()
def mejoralo():
    """MEJORAlo v7.3 — Protocolo de auditoría y mejora de código."""
    pass


@mejoralo.command("scan")
@click.argument("project")
@click.argument("path", type=click.Path(exists=True))
@click.option("--deep", is_flag=True, help="Activa dimensión Psi + análisis profundo")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def mejoralo_scan(project, path, deep, db):
    """X-Ray 13D — Escaneo multidimensional del proyecto."""
    from cortex.mejoralo import MejoraloEngine
    engine = get_engine(db)
    try:
        m = MejoraloEngine(engine)
        with console.status("[bold blue]Ejecutando X-Ray 13D...[/]"):
            result = m.scan(project, path, deep=deep)

        # Score color
        if result.score >= 80:
            score_style = "bold green"
        elif result.score >= 50:
            score_style = "bold yellow"
        else:
            score_style = "bold red"

        table = Table(title=f"🔬 X-Ray 13D — {project}")
        table.add_column("Dimensión", style="bold", width=15)
        table.add_column("Score", width=8)
        table.add_column("Peso", width=10)
        table.add_column("Hallazgos", width=50)

        for d in result.dimensions:
            d_color = "green" if d.score >= 80 else "yellow" if d.score >= 50 else "red"
            findings_str = "; ".join(d.findings[:3]) if d.findings else "—"
            table.add_row(d.name, f"[{d_color}]{d.score}[/]", d.weight, findings_str[:50])

        console.print(table)
        console.print(
            f"\n  Stack: [cyan]{result.stack}[/] | "
            f"Archivos: {result.total_files} | "
            f"LOC: {result.total_loc:,} | "
            f"Score: [{score_style}]{result.score}/100[/]"
        )
        if result.dead_code:
            console.print("  [bold red]☠️  CÓDIGO MUERTO (score < 50)[/]")
    finally:
        engine.close()


@mejoralo.command("record")
@click.argument("project")
@click.option("--before", "score_before", type=int, required=True, help="Score antes")
@click.option("--after", "score_after", type=int, required=True, help="Score después")
@click.option("--action", "-a", "actions", multiple=True, help="Acciones realizadas (repetible)")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def mejoralo_record(project, score_before, score_after, actions, db):
    """Ouroboros — Registrar sesión MEJORAlo en el ledger."""
    from cortex.mejoralo import MejoraloEngine
    engine = get_engine(db)
    try:
        m = MejoraloEngine(engine)
        fact_id = m.record_session(
            project=project,
            score_before=score_before,
            score_after=score_after,
            actions=list(actions),
        )
        delta = score_after - score_before
        color = "green" if delta > 0 else "red" if delta < 0 else "yellow"
        console.print(
            f"[green]✓[/] Sesión registrada [bold]#{fact_id}[/] — "
            f"{score_before} → {score_after} ([{color}]Δ{delta:+d}[/])"
        )
    finally:
        engine.close()


@mejoralo.command("history")
@click.argument("project")
@click.option("--limit", "-n", default=10, help="Máximo de resultados")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def mejoralo_history(project, limit, db):
    """Historial de sesiones MEJORAlo."""
    from cortex.mejoralo import MejoraloEngine
    engine = get_engine(db)
    try:
        m = MejoraloEngine(engine)
        sessions = m.history(project, limit=limit)

        if not sessions:
            console.print(f"[dim]Sin sesiones MEJORAlo para '{project}'.[/]")
            return

        table = Table(title=f"📊 MEJORAlo History — {project}")
        table.add_column("ID", style="bold", width=6)
        table.add_column("Fecha", width=20)
        table.add_column("Score", width=12)
        table.add_column("Δ", width=6)
        table.add_column("Acciones", width=40)

        for s in sessions:
            delta = s.get("delta", 0)
            d_color = "green" if delta and delta > 0 else "red" if delta and delta < 0 else "dim"
            score_str = f"{s.get('score_before', '?')} → {s.get('score_after', '?')}"
            actions_str = ", ".join(s.get("actions", [])[:2]) or "—"
            table.add_row(
                str(s["id"]),
                s["created_at"][:19].replace("T", " "),
                score_str,
                f"[{d_color}]{delta:+d}[/]" if delta is not None else "—",
                actions_str[:40],
            )
        console.print(table)
    finally:
        engine.close()


@mejoralo.command("ship")
@click.argument("project")
@click.argument("path", type=click.Path(exists=True))
@click.option("--db", default=DEFAULT_DB, help="Database path")
def mejoralo_ship(project, path, db):
    """Ship Gate — Los 7 Sellos de producción."""
    from cortex.mejoralo import MejoraloEngine
    engine = get_engine(db)
    try:
        m = MejoraloEngine(engine)
        with console.status("[bold blue]Validando los 7 Sellos...[/]"):
            result = m.ship_gate(project, path)

        for seal in result.seals:
            icon = "[green]✓[/]" if seal.passed else "[red]✗[/]"
            console.print(f"  {icon} {seal.name}: {seal.detail}")

        console.print()
        if result.ready:
            console.print(f"  [bold green]🚀 READY — {result.passed}/{result.total} sellos aprobados[/]")
        else:
            console.print(f"  [bold red]⛔ NOT READY — {result.passed}/{result.total} sellos aprobados[/]")
    finally:
        engine.close()


# ─── Registration ────────────────────────────────────────────────

cli.add_command(ledger)
cli.add_command(timeline)
cli.add_command(launchpad)
cli.add_command(launchpad, name="mission") # Alias for compatibility
cli.add_command(mejoralo)


if __name__ == "__main__":
    cli()

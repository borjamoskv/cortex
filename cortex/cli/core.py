"""CLI commands: init, store, search, recall, history, status, migrate."""

from __future__ import annotations

import asyncio
import json
import sqlite3

import click
from rich.panel import Panel
from rich.table import Table

from cortex import __version__
from cortex.cli import DEFAULT_DB, cli, console, get_engine


def _run_async(coro):
    """Helper to run async coroutines from sync CLI."""
    return asyncio.run(coro)


@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
def init(db) -> None:
    """Initialize CORTEX database."""
    engine = get_engine(db)
    try:
        engine.init_db_sync()
        console.print(
            Panel(
                f"[bold green]✓ CORTEX v{__version__} initialized[/]\nDatabase: {engine._db_path}",
                title="🧠 CORTEX",
                border_style="green",
            )
        )
    finally:
        _run_async(engine.close())


@cli.command()
@click.argument("project")
@click.argument("content")
@click.option("--type", "fact_type", default="knowledge", help="Fact type")
@click.option("--tags", default=None, help="Comma-separated tags")
@click.option("--confidence", default="stated", help="Confidence level")
@click.option("--source", default=None, help="Source of the fact")
@click.option("--ai-time", type=int, default=None, help="AI generation time")
@click.option("--complexity", type=click.Choice(["low", "medium", "high", "god", "impossible"]), default=None, help="Task complexity")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def store(project, content, fact_type, tags, confidence, source, ai_time, complexity, db) -> None:
    """Store a fact in CORTEX."""
    engine = get_engine(db)
    try:
        meta = {}
        if ai_time is not None and complexity is not None:
            from cortex.chronos import ChronosEngine
            import dataclasses
            metrics = ChronosEngine.analyze(ai_time, complexity)
            meta["chronos"] = dataclasses.asdict(metrics)
            console.print(f"[bold cyan]⏳ CHRONOS-1:[/] {metrics.asymmetry_factor:.1f}x asymmetry. {metrics.tip}")
            
        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        fact_id = engine.store_sync(
            project=project,
            content=content,
            fact_type=fact_type,
            tags=tag_list,
            confidence=confidence,
            source=source,
            meta=meta if meta else None,
        )
        console.print(f"[green]✓[/] Stored fact [bold]#{fact_id}[/] in [cyan]{project}[/]")
    finally:
        _run_async(engine.close())


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
            results = engine.search_sync(query, project=project, top_k=top)
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
            table.add_row(str(r.fact_id), r.project, content, r.fact_type, f"{r.score:.2f}")
        console.print(table)
    finally:
        _run_async(engine.close())


@cli.command()
@click.argument("project")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def recall(project, db) -> None:
    """Load full context for a project."""
    engine = get_engine(db)
    try:
        facts = engine.recall_sync(project)
        if not facts:
            console.print(f"[yellow]No facts found for project '{project}'[/]")
            return
        console.print(
            Panel(
                f"[bold]{project}[/] — {len(facts)} active facts",
                title="🧠 CORTEX Recall",
                border_style="cyan",
            )
        )
        by_type: dict[str, list] = {}
        for f in facts:
            by_type.setdefault(f.fact_type, []).append(f)
        for ftype, type_facts in by_type.items():
            console.print(f"\n[bold magenta]═══ {ftype.upper()} ({len(type_facts)}) ═══[/]")
            for f in type_facts:
                tags_str = f" [dim]{', '.join(f.tags)}[/]" if f.tags else ""
                console.print(f"  [dim]#{f.id}[/] {f.content}{tags_str}")
    finally:
        _run_async(engine.close())


@cli.command()
@click.argument("project")
@click.option("--at", "as_of", default=None, help="Point-in-time (ISO 8601)")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def history(project, as_of, db) -> None:
    """Temporal query: what did we know at a specific time?"""
    engine = get_engine(db)
    try:
        facts = engine.history_sync(project, as_of=as_of)
        label = f"as of {as_of}" if as_of else "all time"
        console.print(
            Panel(
                f"[bold]{project}[/] — {len(facts)} facts ({label})",
                title="⏰ CORTEX History",
                border_style="yellow",
            )
        )
        for f in facts:
            status = "[green]●[/]" if f.is_active() else "[red]○[/]"
            console.print(f"  {status} [dim]#{f.id}[/] [{f.valid_from[:10]}] {f.content[:80]}")
    finally:
        _run_async(engine.close())


@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def status(db, json_output) -> None:
    """Show CORTEX health and statistics."""
    engine = get_engine(db)
    try:
        try:
            s = engine.stats_sync()
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
        _run_async(engine.close())


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
        console.print(
            Panel(
                f"[bold green]✓ Migration complete![/]\n"
                f"Facts imported: {stats['facts_imported']}\n"
                f"Errors imported: {stats['errors_imported']}\n"
                f"Bridges imported: {stats['bridges_imported']}\n"
                f"Sessions imported: {stats['sessions_imported']}",
                title="🔄 v3.1 → v4.0 Migration",
                border_style="green",
            )
        )
    finally:
        _run_async(engine.close())


@cli.command("migrate-graph")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def migrate_graph(db) -> None:
    """Migrate local SQLite graph data to Neo4j global knowledge graph."""
    engine = get_engine(db)
    try:
        from cortex.graph import GRAPH_BACKEND, process_fact_graph

        if GRAPH_BACKEND != "neo4j":
            console.print("[yellow]WARNING: CORTEX_GRAPH_BACKEND is not set to 'neo4j'.[/]")
            console.print(
                "[dim]Migration will only re-process data into SQLite unless you set CORTEX_GRAPH_BACKEND=neo4j.[/]"
            )
            if not click.confirm("Do you want to continue?", default=False):
                return
        conn = engine._get_conn()
        facts = conn.execute("SELECT id, content, project, created_at FROM facts").fetchall()
        console.print(f"[bold blue]Migrating {len(facts)} facts to Graph Memory...[/]")
        processed = 0
        with console.status("[bold blue]Processing...[/]") as prog_status:
            for fid, content, project, ts in facts:
                try:
                    process_fact_graph(conn, fid, content, project, ts)
                    processed += 1
                    if processed % 10 == 0:
                        prog_status.update(f"[bold blue]Processed {processed}/{len(facts)}...[/]")
                except Exception as e:
                    console.print(f"[red]✗ Failed at fact #{fid}: {e}[/]")
        console.print(
            Panel(
                f"[bold green]✓ Graph Migration Complete![/]\n"
                f"Facts processed: {processed}\nBackend: {GRAPH_BACKEND}",
                title="🧠 Graph Migration",
                border_style="green",
            )
        )
    finally:
        _run_async(engine.close())

"""
CORTEX v4.0 — CLI Interface.

Command-line tool for the sovereign memory engine.
"""

from __future__ import annotations

import json
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex import __version__
from cortex.engine import CortexEngine
from cortex.timing import TimingTracker

console = Console()
DEFAULT_DB = "~/.cortex/cortex.db"


def get_engine(db: str = DEFAULT_DB) -> CortexEngine:
    """Create an engine instance."""
    return CortexEngine(db_path=db)


def get_tracker(engine: CortexEngine) -> TimingTracker:
    """Create a timing tracker from an engine."""
    return TimingTracker(engine._get_conn())


# ─── Main Group ──────────────────────────────────────────────────

@click.group()
@click.version_option(__version__, prog_name="cortex")
def cli():
    """CORTEX — The Sovereign Ledger for AI Agents."""
    pass


# ─── Init ────────────────────────────────────────────────────────

@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
def init(db):
    """Initialize CORTEX database."""
    engine = get_engine(db)
    engine.init_db()
    console.print(Panel(
        f"[bold green]✓ CORTEX v{__version__} initialized[/]\n"
        f"Database: {engine._db_path}",
        title="🧠 CORTEX",
        border_style="green",
    ))
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
def store(project, content, fact_type, tags, confidence, source, db):
    """Store a fact in CORTEX."""
    engine = get_engine(db)
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
    engine.close()


# ─── Search ──────────────────────────────────────────────────────

@cli.command()
@click.argument("query")
@click.option("--project", "-p", default=None, help="Scope to project")
@click.option("--top", "-k", default=5, help="Number of results")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def search(query, project, top, db):
    """Semantic search across CORTEX memory."""
    engine = get_engine(db)

    with console.status("[bold blue]Searching...[/]"):
        results = engine.search(query, project=project, top_k=top)

    if not results:
        console.print("[yellow]No results found.[/]")
        engine.close()
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
    engine.close()


# ─── Recall ──────────────────────────────────────────────────────

@cli.command()
@click.argument("project")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def recall(project, db):
    """Load full context for a project."""
    engine = get_engine(db)
    facts = engine.recall(project)

    if not facts:
        console.print(f"[yellow]No facts found for project '{project}'[/]")
        engine.close()
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

    engine.close()


# ─── History ─────────────────────────────────────────────────────

@cli.command()
@click.argument("project")
@click.option("--at", "as_of", default=None, help="Point-in-time (ISO 8601)")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def history(project, as_of, db):
    """Temporal query: what did we know at a specific time?"""
    engine = get_engine(db)
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

    engine.close()


# ─── Status ──────────────────────────────────────────────────────

@cli.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def status(db, json_output):
    """Show CORTEX health and statistics."""
    engine = get_engine(db)

    try:
        s = engine.stats()
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        console.print("[dim]Run 'cortex init' first.[/]")
        engine.close()
        return

    if json_output:
        click.echo(json.dumps(s, indent=2))
        engine.close()
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
    engine.close()


# ─── Migrate ─────────────────────────────────────────────────────

@cli.command()
@click.option("--source", default="~/.agent/memory", help="v3.1 memory directory")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def migrate(source, db):
    """Import CORTEX v3.1 data into v4.0."""
    from cortex.migrate import migrate_v31_to_v40

    engine = get_engine(db)
    engine.init_db()

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
    engine.close()


# ─── Time Tracking ───────────────────────────────────────────────

@cli.command("time")
@click.option("--project", "-p", default=None, help="Filter by project")
@click.option("--days", "-d", default=1, help="Number of days (default: 1 = today)")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def time_cmd(project, days, db):
    """Show time tracking summary."""
    engine = get_engine(db)
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
        engine.close()
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
    engine.close()


@cli.command("heartbeat")
@click.argument("project")
@click.argument("entity", default="")
@click.option("--category", "-c", default=None, help="Activity category")
@click.option("--branch", "-b", default=None, help="Git branch")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def heartbeat_cmd(project, entity, category, branch, db):
    """Record an activity heartbeat."""
    engine = get_engine(db)
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
    engine.close()


if __name__ == "__main__":
    cli()

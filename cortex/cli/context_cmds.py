"""
CORTEX v4.0 — Context Engine CLI Commands.

CLI interface for ambient context inference and signal inspection.
"""

import asyncio
import json

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex.cli import DEFAULT_DB, get_engine

console = Console()


@click.group()
def context():
    """Context Engine — ambient intelligence."""
    pass


@context.command("infer")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--persist/--no-persist", default=True, help="Persist snapshot to DB")
@click.option("--json-output", "as_json", is_flag=True, help="Output as JSON")
def infer_cmd(db: str, persist: bool, as_json: bool):
    """Infer current working context from ambient signals."""
    asyncio.run(_infer_async(db, persist, as_json))


async def _infer_async(db: str, persist: bool, as_json: bool):
    from cortex import config
    from cortex.context.collector import ContextCollector
    from cortex.context.inference import ContextInference

    engine = get_engine(db)
    await engine.init_db()

    try:
        conn = await engine.get_conn()
        collector = ContextCollector(
            conn=conn,
            max_signals=config.CONTEXT_MAX_SIGNALS,
            workspace_dir=config.CONTEXT_WORKSPACE_DIR,
            git_enabled=config.CONTEXT_GIT_ENABLED,
        )
        signals = await collector.collect_all()

        inference = ContextInference(conn=conn if persist else None)
        if persist:
            result = await inference.infer_and_persist(signals)
        else:
            result = inference.infer(signals)

        if as_json:
            console.print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
            return

        # Rich output
        confidence_colors = {
            "C5": "green", "C4": "blue", "C3": "yellow", "C2": "red", "C1": "dim red"
        }
        color = confidence_colors.get(result.confidence, "white")

        panel = Panel(
            f"[bold {color}]{result.active_project or 'Unknown'}[/bold {color}]"
            f"  [{color}]{result.confidence}[/{color}]"
            f"  ({result.signals_used} signals)",
            title="🧠 Context Inference",
            subtitle=result.summary[:100],
        )
        console.print(panel)

        if result.projects_ranked:
            table = Table(title="Projects Ranked", show_header=True)
            table.add_column("Project", style="cyan")
            table.add_column("Score", justify="right")
            for project, score in result.projects_ranked[:5]:
                table.add_row(project, f"{score:.4f}")
            console.print(table)

        if result.top_signals:
            table = Table(title="Top Signals", show_header=True)
            table.add_column("Source", style="magenta")
            table.add_column("Type", style="green")
            table.add_column("Content")
            table.add_column("Weight", justify="right")
            for s in result.top_signals[:5]:
                table.add_row(s.source, s.signal_type, s.content[:60], f"{s.weight:.2f}")
            console.print(table)
    finally:
        await engine.close()


@context.command("signals")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--json-output", "as_json", is_flag=True, help="Output as JSON")
def signals_cmd(db: str, as_json: bool):
    """Show raw ambient signals."""
    asyncio.run(_signals_async(db, as_json))


async def _signals_async(db: str, as_json: bool):
    from cortex import config
    from cortex.context.collector import ContextCollector

    engine = get_engine(db)
    await engine.init_db()

    try:
        conn = await engine.get_conn()
        collector = ContextCollector(
            conn=conn,
            max_signals=config.CONTEXT_MAX_SIGNALS,
            workspace_dir=config.CONTEXT_WORKSPACE_DIR,
            git_enabled=config.CONTEXT_GIT_ENABLED,
        )
        signals = await collector.collect_all()

        if as_json:
            console.print(json.dumps([s.to_dict() for s in signals], indent=2, ensure_ascii=False))
            return

        if not signals:
            console.print("[dim]No signals detected.[/dim]")
            return

        table = Table(title=f"🔊 Ambient Signals ({len(signals)})", show_header=True)
        table.add_column("Source", style="magenta")
        table.add_column("Type", style="green")
        table.add_column("Project", style="cyan")
        table.add_column("Content")
        table.add_column("Weight", justify="right")
        for s in signals:
            table.add_row(
                s.source, s.signal_type, s.project or "—",
                s.content[:50], f"{s.weight:.2f}",
            )
        console.print(table)
    finally:
        await engine.close()


@context.command("history")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--limit", default=10, help="Number of snapshots")
@click.option("--json-output", "as_json", is_flag=True, help="Output as JSON")
def history_cmd(db: str, limit: int, as_json: bool):
    """Show past context inference snapshots."""
    asyncio.run(_history_async(db, limit, as_json))


async def _history_async(db: str, limit: int, as_json: bool):
    from cortex.context.inference import ContextInference

    engine = get_engine(db)
    await engine.init_db()

    try:
        conn = await engine.get_conn()
        inference = ContextInference(conn=conn)
        snapshots = await inference.get_history(limit=limit)

        if as_json:
            console.print(json.dumps(snapshots, indent=2, ensure_ascii=False))
            return

        if not snapshots:
            console.print("[dim]No context snapshots found.[/dim]")
            return

        table = Table(title=f"📸 Context Snapshots ({len(snapshots)})", show_header=True)
        table.add_column("ID", style="dim")
        table.add_column("Project", style="cyan")
        table.add_column("Confidence", style="bold")
        table.add_column("Signals", justify="right")
        table.add_column("Created At")
        for snap in snapshots:
            table.add_row(
                str(snap["id"]),
                snap.get("active_project") or "—",
                snap["confidence"],
                str(snap["signals_used"]),
                snap.get("created_at", ""),
            )
        console.print(table)
    finally:
        await engine.close()

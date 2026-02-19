"""CLI commands: handoff generate, handoff load."""

from __future__ import annotations

import asyncio
import json

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli import DEFAULT_DB, cli, console, get_engine
from cortex.handoff import generate_handoff, load_handoff, save_handoff


def _run_async(coro):
    """Helper to run async coroutines from sync CLI."""
    return asyncio.run(coro)


@cli.group()
def handoff() -> None:
    """Session Handoff Protocol — compact session continuity."""
    pass


@handoff.command("generate")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--pending", "-p", multiple=True, help="Pending work items (repeat for multiple)")
@click.option("--mood", "-m", default="neutral", help="Session mood (e.g. productive, blocked, exploring)")
@click.option("--focus", "-f", multiple=True, help="Focus projects (repeat for multiple)")
@click.option("--out", default=None, help="Output path (default: ~/.cortex/handoff.json)")
def generate(db, pending, mood, focus, out) -> None:
    """Generate a session handoff from current CORTEX state."""
    from pathlib import Path

    engine = get_engine(db)
    try:
        session_meta = {
            "focus_projects": list(focus),
            "pending_work": list(pending),
            "mood": mood,
        }

        with console.status("[bold blue]Generating handoff...[/]"):
            data = _run_async(generate_handoff(engine, session_meta=session_meta))

        out_path = Path(out) if out else None
        saved_path = save_handoff(data, path=out_path)

        # Display summary
        console.print(
            Panel(
                f"[bold green]✓ Handoff generated[/]\n"
                f"Decisions: {len(data['hot_decisions'])} | "
                f"Ghosts: {len(data['active_ghosts'])} | "
                f"Errors: {len(data['recent_errors'])} | "
                f"Active projects: {len(data['active_projects'])}\n"
                f"Saved to: {saved_path}",
                title="🤝 Session Handoff",
                border_style="cyan",
            )
        )
    finally:
        _run_async(engine.close())


@handoff.command("load")
@click.option("--path", default=None, help="Path to handoff.json")
@click.option("--json-output", is_flag=True, help="Output raw JSON")
def load(path, json_output) -> None:
    """Load and display the current session handoff."""
    from pathlib import Path as P

    target = P(path) if path else None
    data = load_handoff(path=target)

    if data is None:
        console.print("[yellow]No handoff found. Run 'cortex handoff generate' first.[/]")
        return

    if json_output:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return

    # Pretty display
    session = data.get("session", {})
    stats = data.get("stats", {})

    console.print(
        Panel(
            f"[dim]Generated:[/] {data.get('generated_at', '?')}\n"
            f"[dim]Mood:[/] {session.get('mood', '?')} | "
            f"[dim]Focus:[/] {', '.join(session.get('focus_projects', [])) or 'none'}\n"
            f"[dim]Facts:[/] {stats.get('total_facts', 0)} | "
            f"[dim]Projects:[/] {stats.get('total_projects', 0)} | "
            f"[dim]DB:[/] {stats.get('db_size_mb', 0)} MB",
            title="🤝 Session Handoff",
            border_style="cyan",
        )
    )

    # Pending work
    pending = session.get("pending_work", [])
    if pending:
        console.print("\n[bold yellow]⏳ Pending Work[/]")
        for item in pending:
            console.print(f"  • {item}")

    # Hot decisions
    decisions = data.get("hot_decisions", [])
    if decisions:
        table = Table(title="\n🔥 Hot Decisions")
        table.add_column("#", style="dim", width=4)
        table.add_column("Project", style="cyan", width=15)
        table.add_column("Decision", width=55)
        for d in decisions:
            content = d["content"][:70] + "..." if len(d["content"]) > 70 else d["content"]
            table.add_row(str(d["id"]), d["project"], content)
        console.print(table)

    # Active ghosts
    ghosts = data.get("active_ghosts", [])
    if ghosts:
        table = Table(title="\n👻 Active Ghosts")
        table.add_column("#", style="dim", width=4)
        table.add_column("Project", style="cyan", width=15)
        table.add_column("Reference", width=55)
        for g in ghosts:
            ref = g["reference"][:70] + "..." if len(g["reference"]) > 70 else g["reference"]
            table.add_row(str(g["id"]), g["project"], ref)
        console.print(table)

    # Recent errors
    errors = data.get("recent_errors", [])
    if errors:
        table = Table(title="\n🔴 Recent Errors")
        table.add_column("#", style="dim", width=4)
        table.add_column("Project", style="red", width=15)
        table.add_column("Error", width=55)
        for e in errors:
            content = e["content"][:70] + "..." if len(e["content"]) > 70 else e["content"]
            table.add_row(str(e["id"]), e["project"], content)
        console.print(table)

    # Active projects
    active = data.get("active_projects", [])
    if active:
        console.print(f"\n[bold green]📂 Active Projects (24h):[/] {', '.join(active)}")

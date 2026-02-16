"""CLI commands: launchpad (launch, list)."""

from __future__ import annotations

import os

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli import cli, console, get_engine, DEFAULT_DB
from cortex.launchpad import MissionOrchestrator


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
                project=project, goal=goal, formation=formation,
                agents=agents, mission_file=mission_file
            )
        if result["status"] == "success":
            console.print(Panel(
                f"[bold green]✓ Mission Launched Successfully[/]\n"
                f"Intent ID: [cyan]#{result['intent_id']}[/]\n"
                f"Result ID: [cyan]#{result['result_id']}[/]\n"
                f"Status: {result['status'].upper()}",
                title="🐝 Mission Control", border_style="green",
            ))
            console.print(f"\n[dim]Recent Output:[/]\n{result['stdout'][-500:]}")
        else:
            console.print(Panel(
                f"[bold red]✗ Mission Failed[/]\n"
                f"Intent ID: {result.get('intent_id', 'N/A')}\n"
                f"Error: {result.get('error', 'Check stderr')}",
                title="🐝 Mission Control", border_style="red",
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
                str(m["id"]), m["project"], m["fact_type"],
                m["content"][:50] + "...", m["created_at"]
            )
        console.print(table)
    finally:
        engine.close()

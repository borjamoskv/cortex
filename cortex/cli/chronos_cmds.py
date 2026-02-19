"""
Commands for CHRONOS-1 The Senior Benchmark.

Exposes the native API to calculate Human vs AI asymmetry.
"""

import click
from rich.console import Console
from rich.panel import Panel

from cortex.chronos import ChronosEngine

console = Console()

@click.group(name="chronos")
def chronos_cmds() -> None:
    """CHRONOS-1 — Benchmark of Senior Human Time vs AI Swarm Time."""
    pass


@chronos_cmds.command()
@click.option(
    "--ai-time",
    "-t",
    type=float,
    required=True,
    help="Time it took the AI swarm to complete the task (in seconds).",
)
@click.option(
    "--complexity",
    "-c",
    type=click.Choice(["low", "medium", "high", "god"], case_sensitive=False),
    default="medium",
    help="Task complexity multiplier level.",
)
def analyze(ai_time: float, complexity: str) -> None:
    """
    Analyzes the task asymmetry. Example:
    cortex chronos analyze --ai-time 120 --complexity high
    """
    try:
        metrics = ChronosEngine.analyze(ai_time, complexity)
        
        # Formatting
        human_time_str = ChronosEngine.format_time(metrics.human_time_secs)
        ai_time_str = ChronosEngine.format_time(metrics.ai_time_secs)
        
        content = (
            f"\n[cyan]⏱️  Human Senior Time:  [/cyan][white]{human_time_str}[/white]\n"
            f"[magenta]⚡ MOSKV Swarm Time:   [/magenta][white]{ai_time_str}[/white]\n"
            f"[green]🌌 Tactical Asymmetry: [/green][bold white]{metrics.asymmetry_factor}x[/bold white]\n\n"
            f"[dim]{metrics.context_msg}[/dim]\n\n"
            f"💡 [bold yellow]{metrics.tip}[/bold yellow]\n"
            f"⚠️  [dim red]{metrics.anti_tip}[/dim red]"
        )
        
        panel = Panel(
            content,
            title="[bold magenta]🕒 CHRONOS-1 — SENIOR BENCHMARK[/bold magenta]",
            border_style="magenta",
            expand=False
        )
        
        console.print(panel)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

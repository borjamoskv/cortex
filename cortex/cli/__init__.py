"""
CORTEX CLI — Package init.

Re-exports the main CLI group and shared utilities.
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
from cortex.timing import TimingTracker
from cortex.config import DEFAULT_DB_PATH

console = Console()
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


# ─── Register all sub-modules ───────────────────────────────────
from cortex.cli import core  # noqa: E402, F401
from cortex.cli import sync_cmds  # noqa: E402, F401
from cortex.cli import crud  # noqa: E402, F401
from cortex.cli import time_cmds  # noqa: E402, F401
from cortex.cli import vote_ledger  # noqa: E402, F401
from cortex.cli import timeline_cmds  # noqa: E402, F401
from cortex.cli import launchpad_cmds  # noqa: E402, F401
from cortex.cli import mejoralo_cmds  # noqa: E402, F401

# ─── Registration ────────────────────────────────────────────────
from cortex.cli.time_cmds import time_cmd, heartbeat_cmd  # noqa: E402
from cortex.cli.vote_ledger import ledger  # noqa: E402
from cortex.cli.timeline_cmds import timeline  # noqa: E402
from cortex.cli.launchpad_cmds import launchpad  # noqa: E402
from cortex.cli.mejoralo_cmds import mejoralo  # noqa: E402

cli.add_command(time_cmd, name="time")
cli.add_command(heartbeat_cmd, name="heartbeat")
cli.add_command(ledger)
cli.add_command(timeline)
cli.add_command(launchpad)
cli.add_command(launchpad, name="mission")  # Alias for compatibility
cli.add_command(mejoralo)


if __name__ == "__main__":
    cli()

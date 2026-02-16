"""
CORTEX CLI — Package init.

Re-exports the main CLI group and shared utilities.
"""

import click
from rich.console import Console

from cortex import __version__
from cortex.config import DEFAULT_DB_PATH
from cortex.engine import CortexEngine
from cortex.timing import TimingTracker

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
    """CORTEX — El Registro Soberano para Agentes de IA."""
    pass


# ─── Registrar todos los sub-módulos ───────────────────────────────────
from cortex.cli import (
    core,  # noqa: E402, F401
    crud,  # noqa: E402, F401
    launchpad_cmds,  # noqa: E402, F401
    mejoralo_cmds,  # noqa: E402, F401
    sync_cmds,  # noqa: E402, F401
    time_cmds,  # noqa: E402, F401
    timeline_cmds,  # noqa: E402, F401
    vote_ledger,  # noqa: E402, F401
)
from cortex.cli.launchpad_cmds import launchpad  # noqa: E402
from cortex.cli.mejoralo_cmds import mejoralo  # noqa: E402

# ─── Registro de comandos ───────────────────────────────────────────────
from cortex.cli.time_cmds import heartbeat_cmd, time_cmd  # noqa: E402
from cortex.cli.timeline_cmds import timeline  # noqa: E402
from cortex.cli.vote_ledger import ledger  # noqa: E402

cli.add_command(time_cmd, name="time")
cli.add_command(heartbeat_cmd, name="heartbeat")
cli.add_command(ledger)
cli.add_command(timeline)
cli.add_command(launchpad)
cli.add_command(launchpad, name="mission")  # Alias por compatibilidad
cli.add_command(mejoralo)


if __name__ == "__main__":
    cli()

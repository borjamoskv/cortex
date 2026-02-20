"""AUTOROUTER-1 — CLI commands for CORTEX integration.

Commands:
  cortex autorouter start    → Arranca el daemon
  cortex autorouter stop     → Detiene el daemon
  cortex autorouter status   → Estado actual
  cortex autorouter history  → Historial de mutaciones
  cortex autorouter test     → Test rápido
  cortex autorouter config   → Genera config personalizable
  cortex autorouter enable-boot → Instala en launchd para auto-arranque
  cortex autorouter disable-boot→ Desinstala de launchd
  cortex autorouter logs     → Tail al log del daemon
"""

import sys
import subprocess
import os
from pathlib import Path

import click
from rich.console import Console

console = Console()

DAEMON_SCRIPT = (
    Path.home()
    / ".gemini"
    / "antigravity"
    / "skills"
    / "autorouter-1"
    / "scripts"
    / "autorouter_daemon.py"
)


def _run_daemon(args: list[str]) -> int:
    """Ejecuta el daemon script con los argumentos dados."""
    if not DAEMON_SCRIPT.exists():
        console.print(
            f"[bold red]Error:[/] AUTOROUTER-1 no encontrado en {DAEMON_SCRIPT}"
        )
        sys.exit(1)
    try:
        result = subprocess.run(
            ["python3", str(DAEMON_SCRIPT)] + args, check=False
        )
        return result.returncode
    except (OSError, ValueError, KeyError) as e:
        console.print(f"[bold red]Error de ejecución:[/] {e}")
        sys.exit(1)


@click.group(name="autorouter")
def autorouter_cmds():
    """⚡ AUTOROUTER-1 v3.0: Cognitive Switch Engine.

    Daemon soberano que muta el modelo de IA según el modo de operación.
    """
    pass


@autorouter_cmds.command()
@click.option("--background", "-bg", is_flag=True, help="Arrancar en background")
def start(background):
    """Arrancar el daemon de ruteo cognitivo."""
    if background:
        console.print("[bold cyan]🚀 Arrancando AUTOROUTER-1 en background...[/]")
        log_file = Path.home() / ".cortex" / "router_daemon.log"
        subprocess.Popen(
            ["python3", str(DAEMON_SCRIPT)],
            stdout=open(log_file, "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        console.print(f"[green]✓[/] Daemon arrancado. Log: {log_file}")
    else:
        _run_daemon([])


@autorouter_cmds.command()
def stop():
    """Detener el daemon limpiamente."""
    code = _run_daemon(["--stop"])
    if code != 0:
        sys.exit(code)


@autorouter_cmds.command(name="status")
def router_status():
    """Mostrar estado del daemon."""
    code = _run_daemon(["--status"])
    if code != 0:
        sys.exit(code)


@autorouter_cmds.command()
@click.option("-n", default=20, help="Número de entradas a mostrar")
def history(n):
    """Ver historial de mutaciones cognitivas."""
    code = _run_daemon(["--history", str(n)])
    if code != 0:
        sys.exit(code)


@autorouter_cmds.command()
def test():
    """Test rápido de todas las funciones."""
    code = _run_daemon(["--test"])
    if code != 0:
        sys.exit(code)


@autorouter_cmds.command()
def config():
    """Generar autorouter.config.json personalizable."""
    code = _run_daemon(["--init-config"])
    if code != 0:
        sys.exit(code)


PLIST_NAME = "com.moskv.autorouter.plist"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / PLIST_NAME


@autorouter_cmds.command(name="enable-boot")
def enable_boot():
    """Instala AUTOROUTER-1 en launchd para inicio automático en macOS."""
    if not sys.platform == "darwin":
        console.print("[bold red]❌ Error:[/] launchd solo está disponible en macOS.")
        sys.exit(1)

    python_path = sys.executable
    script_path = str(DAEMON_SCRIPT)
    log_path = str(Path.home() / ".cortex" / "router_daemon.log")

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.moskv.autorouter</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{script_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    <key>StandardErrorPath</key>
    <string>{log_path}</string>
</dict>
</plist>"""

    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(PLIST_PATH, "w") as f:
        f.write(plist_content)
    
    console.print(f"[cyan]ℹ️ Creado plist en {PLIST_PATH}[/]")
    
    # Cargar en launchd
    try:
        # Descargar primero por si ya existía
        subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True)
        # Cargar
        res = subprocess.run(["launchctl", "load", str(PLIST_PATH)], capture_output=True, text=True)
        if res.returncode == 0:
            console.print("[bold green]✅ AUTOROUTER-1 instalado y arrancado vía launchd.[/]")
            console.print("[dim]Se iniciará automáticamente al hacer login.[/]")
        else:
            console.print(f"[bold red]❌ Error al cargar launchd:[/] {res.stderr}")
    except (OSError, ValueError, KeyError) as e:
        console.print(f"[bold red]❌ Excepción:[/] {e}")


@autorouter_cmds.command(name="disable-boot")
def disable_boot():
    """Desinstala AUTOROUTER-1 de launchd."""
    if not sys.platform == "darwin":
        console.print("[bold red]❌ Error:[/] launchd solo está disponible en macOS.")
        sys.exit(1)

    if not PLIST_PATH.exists():
        console.print("[yellow]⚠️ No hay configuración launchd instalada.[/]")
        return

    try:
        subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True)
        PLIST_PATH.unlink()
        console.print("[bold green]✅ AUTOROUTER-1 desinstalado de launchd.[/]")
        
        # Parar también una posible instancia
        _run_daemon(["--stop"])
    except (OSError, ValueError, KeyError) as e:
        console.print(f"[bold red]❌ Error:[/] {e}")


@autorouter_cmds.command()
def logs():
    """Sigue (tail -f) los logs del daemon en tiempo real."""
    log_file = Path.home() / ".cortex" / "router_daemon.log"
    if not log_file.exists():
        console.print(f"[yellow]⚠️ No se encontró log en {log_file}[/]")
        sys.exit(1)
        
    console.print(f"[dim]Mostrando logs de: {log_file} (Ctrl+C para salir)[/]")
    try:
        subprocess.run(["tail", "-f", str(log_file)])
    except KeyboardInterrupt:
        pass


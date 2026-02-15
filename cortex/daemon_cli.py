"""
CORTEX v4.0 — MOSKV-1 Daemon CLI.

Command-line interface for the persistent watchdog.

Commands:
    moskv-daemon start       Run daemon in foreground
    moskv-daemon check       Run once and exit
    moskv-daemon status      Show last check results
    moskv-daemon install     Install macOS launchd agent
    moskv-daemon uninstall   Remove macOS launchd agent
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path

from cortex.daemon import (
    BUNDLE_ID,
    DEFAULT_INTERVAL,
    DEFAULT_MEMORY_STALE_HOURS,
    DEFAULT_STALE_HOURS,
    MoskvDaemon,
)

PLIST_SOURCE = Path(__file__).parent.parent / "launchd" / f"{BUNDLE_ID}.plist"
PLIST_DEST = Path.home() / "Library" / "LaunchAgents" / f"{BUNDLE_ID}.plist"


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_start(args: argparse.Namespace) -> None:
    """Run daemon in foreground."""
    daemon = MoskvDaemon(
        sites=args.sites.split(",") if args.sites else None,
        stale_hours=args.stale_hours,
        memory_stale_hours=args.memory_stale_hours,
        notify=not args.no_notify,
    )
    daemon.run(interval=args.interval)


def cmd_check(args: argparse.Namespace) -> None:
    """Run all checks once and print results."""
    daemon = MoskvDaemon(
        sites=args.sites.split(",") if args.sites else None,
        stale_hours=args.stale_hours,
        memory_stale_hours=args.memory_stale_hours,
        notify=not args.no_notify,
    )
    status = daemon.check()

    # Print summary
    print()
    print("╔══════════════════════════════════════╗")
    print("║     MOSKV-1 DAEMON — CHECK           ║")
    print("╚══════════════════════════════════════╝")
    print()

    # Sites
    print("▸ SITES")
    for site in status.sites:
        icon = "🟢" if site.healthy else "🔴"
        ms = f"{site.response_ms:.0f}ms" if site.healthy else site.error
        print(f"  {icon} {site.url} — {ms}")
    print()

    # Ghosts
    print("▸ STALE PROJECTS")
    if status.stale_ghosts:
        for g in status.stale_ghosts:
            print(f"  💤 {g.project} — {g.hours_stale:.0f}h sin actividad")
    else:
        print("  ✅ All projects active")
    print()

    # Memory
    print("▸ CORTEX MEMORY")
    if status.memory_alerts:
        for m in status.memory_alerts:
            print(f"  ⚠️  {m.file} — {m.hours_stale:.0f}h stale")
    else:
        print("  ✅ Memory fresh")
    print()

    # Summary
    if status.all_healthy:
        print("═══ ✅ ALL SYSTEMS NOMINAL ═══")
    else:
        issues = len(status.sites) - sum(1 for s in status.sites if s.healthy)
        issues += len(status.stale_ghosts) + len(status.memory_alerts)
        print(f"═══ ⚠️  {issues} ISSUE(S) DETECTED ═══")

    sys.exit(0 if status.all_healthy else 1)


def cmd_status(args: argparse.Namespace) -> None:
    """Show last check results from disk."""
    status = MoskvDaemon.load_status()
    if not status:
        print("No daemon status found. Run 'moskv-daemon check' first.")
        sys.exit(1)

    print(json.dumps(status, indent=2, ensure_ascii=False))


def cmd_install(args: argparse.Namespace) -> None:
    """Install launchd agent."""
    if not PLIST_SOURCE.exists():
        print(f"❌ Plist not found: {PLIST_SOURCE}")
        sys.exit(1)

    PLIST_DEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PLIST_SOURCE, PLIST_DEST)
    print(f"✅ Installed: {PLIST_DEST}")

    import subprocess
    subprocess.run(["launchctl", "load", str(PLIST_DEST)], check=False)
    print(f"✅ Loaded: {BUNDLE_ID}")
    print("   Daemon will run every 5 minutes and on login.")


def cmd_uninstall(args: argparse.Namespace) -> None:
    """Remove launchd agent."""
    import subprocess

    if PLIST_DEST.exists():
        subprocess.run(["launchctl", "unload", str(PLIST_DEST)], check=False)
        PLIST_DEST.unlink()
        print(f"✅ Removed: {BUNDLE_ID}")
    else:
        print("No launchd agent installed.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="moskv-daemon",
        description="MOSKV-1 Persistent Watchdog Daemon",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "--sites",
        help="Comma-separated URLs to monitor (default: naroa.online)",
    )
    parser.add_argument(
        "--stale-hours",
        type=float,
        default=DEFAULT_STALE_HOURS,
        help=f"Hours before a ghost project is stale (default: {DEFAULT_STALE_HOURS})",
    )
    parser.add_argument(
        "--memory-stale-hours",
        type=float,
        default=DEFAULT_MEMORY_STALE_HOURS,
        help=f"Hours before CORTEX memory is stale (default: {DEFAULT_MEMORY_STALE_HOURS})",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        help=f"Check interval in seconds (default: {DEFAULT_INTERVAL})",
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Disable macOS notifications",
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("start", help="Run daemon in foreground")
    sub.add_parser("check", help="Run checks once and exit")
    sub.add_parser("status", help="Show last check results")
    sub.add_parser("install", help="Install macOS launchd agent")
    sub.add_parser("uninstall", help="Remove macOS launchd agent")

    args = parser.parse_args()
    setup_logging(args.verbose)

    commands = {
        "start": cmd_start,
        "check": cmd_check,
        "status": cmd_status,
        "install": cmd_install,
        "uninstall": cmd_uninstall,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

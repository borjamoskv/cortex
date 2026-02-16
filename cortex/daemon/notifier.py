"""macOS native notifications for MOSKV-1 daemon."""

from __future__ import annotations

import logging
import subprocess

from cortex.daemon.models import GhostAlert, MemoryAlert, SiteStatus

logger = logging.getLogger("moskv-daemon")


class Notifier:
    """macOS native notifications via osascript."""

    @staticmethod
    def notify(title: str, message: str, sound: str = "Submarine") -> bool:
        """Send a macOS notification. Returns True on success."""
        script = f'display notification "{message}" with title "{title}" sound name "{sound}"'
        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=5,
            )
            return True
        except (subprocess.SubprocessError, OSError) as e:
            logger.warning("Notification failed: %s", e)
            return False

    @staticmethod
    def alert_site_down(site: SiteStatus) -> None:
        Notifier.notify(
            "⚠️ MOSKV-1 — Site Down",
            f"{site.url} is unreachable: {site.error or f'HTTP {site.status_code}'}",
            sound="Basso",
        )

    @staticmethod
    def alert_stale_project(ghost: GhostAlert) -> None:
        hours = int(ghost.hours_stale)
        Notifier.notify(
            "💤 MOSKV-1 — Proyecto Stale",
            f"{ghost.project} lleva {hours}h sin actividad",
        )

    @staticmethod
    def alert_memory_stale(alert: MemoryAlert) -> None:
        hours = int(alert.hours_stale)
        Notifier.notify(
            "🧠 MOSKV-1 — CORTEX Stale",
            f"{alert.file} sin actualizar ({hours}h). Ejecuta /memoria",
        )

"""
CORTEX v4.0 — MOSKV-1 Daemon.

Persistent watchdog that gives MOSKV-1 three capabilities:
1. Persistent Vision: HTTP health checks on monitored URLs
2. Temporal Initiative: Stale project detection from ghosts.json
3. Automatic Memory: CORTEX freshness monitoring

Runs as a launchd agent on macOS, checking every 5 minutes.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("moskv-daemon")

# ─── Constants ────────────────────────────────────────────────────────

DEFAULT_INTERVAL = 300  # 5 minutes
DEFAULT_STALE_HOURS = 48  # ghost projects stale after 48h
DEFAULT_MEMORY_STALE_HOURS = 24  # system.json stale after 24h
DEFAULT_TIMEOUT = 10  # HTTP timeout seconds
AGENT_DIR = Path.home() / ".agent"
STATUS_FILE = AGENT_DIR / "memory" / "daemon_status.json"
BUNDLE_ID = "com.moskv.daemon"


# ─── Data Classes ─────────────────────────────────────────────────────


@dataclass
class SiteStatus:
    """Result of a single site health check."""
    url: str
    healthy: bool
    status_code: int = 0
    response_ms: float = 0.0
    error: str = ""
    checked_at: str = ""


@dataclass
class GhostAlert:
    """A stale project detected from ghosts.json."""
    project: str
    last_activity: str
    hours_stale: float
    mood: str = ""
    blocked_by: str | None = None


@dataclass
class MemoryAlert:
    """CORTEX memory freshness alert."""
    file: str
    last_updated: str
    hours_stale: float


@dataclass
class DaemonStatus:
    """Full daemon check result — persisted to disk."""
    checked_at: str
    sites: list[SiteStatus] = field(default_factory=list)
    stale_ghosts: list[GhostAlert] = field(default_factory=list)
    memory_alerts: list[MemoryAlert] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def all_healthy(self) -> bool:
        return (
            all(s.healthy for s in self.sites)
            and len(self.stale_ghosts) == 0
            and len(self.memory_alerts) == 0
            and len(self.errors) == 0
        )

    def to_dict(self) -> dict:
        return {
            "checked_at": self.checked_at,
            "all_healthy": self.all_healthy,
            "sites": [
                {
                    "url": s.url,
                    "healthy": s.healthy,
                    "status_code": s.status_code,
                    "response_ms": round(s.response_ms, 1),
                    "error": s.error,
                    "checked_at": s.checked_at,
                }
                for s in self.sites
            ],
            "stale_ghosts": [
                {
                    "project": g.project,
                    "last_activity": g.last_activity,
                    "hours_stale": round(g.hours_stale, 1),
                    "mood": g.mood,
                    "blocked_by": g.blocked_by,
                }
                for g in self.stale_ghosts
            ],
            "memory_alerts": [
                {
                    "file": m.file,
                    "last_updated": m.last_updated,
                    "hours_stale": round(m.hours_stale, 1),
                }
                for m in self.memory_alerts
            ],
            "errors": self.errors,
        }


# ─── Notifier ─────────────────────────────────────────────────────────


class Notifier:
    """macOS native notifications via osascript."""

    @staticmethod
    def notify(title: str, message: str, sound: str = "Submarine") -> bool:
        """Send a macOS notification. Returns True on success."""
        script = (
            f'display notification "{message}" '
            f'with title "{title}" '
            f'sound name "{sound}"'
        )
        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=5,
            )
            return True
        except Exception as e:
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


# ─── Site Monitor ─────────────────────────────────────────────────────


class SiteMonitor:
    """HTTP health checker for monitored URLs."""

    def __init__(
        self,
        urls: list[str],
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.urls = urls
        self.timeout = timeout

    def check_all(self) -> list[SiteStatus]:
        """Check all URLs. Returns list of SiteStatus."""
        results = []
        for url in self.urls:
            results.append(self._check_one(url))
        return results

    def _check_one(self, url: str) -> SiteStatus:
        """Check a single URL."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            start = time.monotonic()
            resp = httpx.get(url, timeout=self.timeout, follow_redirects=True)
            elapsed = (time.monotonic() - start) * 1000

            healthy = 200 <= resp.status_code < 400
            return SiteStatus(
                url=url,
                healthy=healthy,
                status_code=resp.status_code,
                response_ms=elapsed,
                checked_at=now,
                error="" if healthy else f"HTTP {resp.status_code}",
            )
        except httpx.TimeoutException:
            return SiteStatus(url=url, healthy=False, error="timeout", checked_at=now)
        except httpx.ConnectError:
            return SiteStatus(url=url, healthy=False, error="connection refused", checked_at=now)
        except Exception as e:
            return SiteStatus(url=url, healthy=False, error=str(e)[:100], checked_at=now)


# ─── Ghost Watcher ────────────────────────────────────────────────────


class GhostWatcher:
    """Monitors ghosts.json for stale projects."""

    def __init__(
        self,
        ghosts_path: Path = AGENT_DIR / "memory" / "ghosts.json",
        stale_hours: float = DEFAULT_STALE_HOURS,
    ):
        self.ghosts_path = ghosts_path
        self.stale_hours = stale_hours

    def check(self) -> list[GhostAlert]:
        """Return list of projects that are stale."""
        if not self.ghosts_path.exists():
            return []

        try:
            ghosts = json.loads(self.ghosts_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to read ghosts.json: %s", e)
            return []

        now = datetime.now(timezone.utc)
        stale = []

        for project, data in ghosts.items():
            ts = data.get("timestamp", "")
            if not ts:
                continue

            # Skip explicitly blocked projects
            if data.get("blocked_by"):
                continue

            try:
                last = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                hours = (now - last).total_seconds() / 3600

                if hours > self.stale_hours:
                    stale.append(GhostAlert(
                        project=project,
                        last_activity=ts,
                        hours_stale=hours,
                        mood=data.get("mood", ""),
                        blocked_by=data.get("blocked_by"),
                    ))
            except (ValueError, TypeError):
                continue

        return stale


# ─── Memory Syncer ────────────────────────────────────────────────────


class MemorySyncer:
    """Monitors CORTEX memory files for staleness."""

    def __init__(
        self,
        system_path: Path = AGENT_DIR / "memory" / "system.json",
        stale_hours: float = DEFAULT_MEMORY_STALE_HOURS,
    ):
        self.system_path = system_path
        self.stale_hours = stale_hours

    def check(self) -> list[MemoryAlert]:
        """Return alerts for stale memory files."""
        alerts = []

        if not self.system_path.exists():
            return alerts

        try:
            data = json.loads(self.system_path.read_text())
            ts = data.get("meta", {}).get("last_updated", "")
            if not ts:
                return alerts

            last = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            hours = (now - last).total_seconds() / 3600

            if hours > self.stale_hours:
                alerts.append(MemoryAlert(
                    file="system.json",
                    last_updated=ts,
                    hours_stale=hours,
                ))
        except (json.JSONDecodeError, OSError, ValueError) as e:
            logger.error("Failed to check system.json: %s", e)

        return alerts


# ─── Main Daemon ──────────────────────────────────────────────────────


class MoskvDaemon:
    """MOSKV-1 persistent watchdog.

    Orchestrates all monitors and sends alerts.

    Usage:
        daemon = MoskvDaemon()
        daemon.check()           # Run once
        daemon.run(interval=300) # Run forever
    """

    def __init__(
        self,
        sites: list[str] | None = None,
        config_dir: Path = AGENT_DIR / "memory",
        stale_hours: float = DEFAULT_STALE_HOURS,
        memory_stale_hours: float = DEFAULT_MEMORY_STALE_HOURS,
        notify: bool = True,
    ):
        self.notify_enabled = notify
        self.config_dir = config_dir

        default_sites = ["https://naroa.online"]
        self.site_monitor = SiteMonitor(sites or default_sites)
        self.ghost_watcher = GhostWatcher(config_dir / "ghosts.json", stale_hours)
        self.memory_syncer = MemorySyncer(config_dir / "system.json", memory_stale_hours)

        self._last_alerts: dict[str, float] = {}  # cooldown tracker
        self._cooldown = 3600  # 1 hour between duplicate alerts

    def check(self) -> DaemonStatus:
        """Run all checks once. Returns DaemonStatus."""
        now = datetime.now(timezone.utc).isoformat()
        status = DaemonStatus(checked_at=now)

        # 1. Site checks
        try:
            status.sites = self.site_monitor.check_all()
            for site in status.sites:
                if not site.healthy and self._should_alert(f"site:{site.url}"):
                    Notifier.alert_site_down(site)
        except Exception as e:
            status.errors.append(f"Site monitor error: {e}")
            logger.exception("Site monitor failed")

        # 2. Ghost checks
        try:
            status.stale_ghosts = self.ghost_watcher.check()
            for ghost in status.stale_ghosts:
                if self._should_alert(f"ghost:{ghost.project}"):
                    Notifier.alert_stale_project(ghost)
        except Exception as e:
            status.errors.append(f"Ghost watcher error: {e}")
            logger.exception("Ghost watcher failed")

        # 3. Memory checks
        try:
            status.memory_alerts = self.memory_syncer.check()
            for alert in status.memory_alerts:
                if self._should_alert(f"memory:{alert.file}"):
                    Notifier.alert_memory_stale(alert)
        except Exception as e:
            status.errors.append(f"Memory syncer error: {e}")
            logger.exception("Memory syncer failed")

        # Persist status
        self._save_status(status)

        level = "✅" if status.all_healthy else "⚠️"
        logger.info(
            "%s Check complete: %d sites, %d stale ghosts, %d memory alerts",
            level, len(status.sites), len(status.stale_ghosts), len(status.memory_alerts),
        )

        return status

    def run(self, interval: int = DEFAULT_INTERVAL) -> None:
        """Run checks in a loop forever."""
        logger.info("🚀 MOSKV-1 Daemon starting (interval=%ds)", interval)
        try:
            while True:
                self.check()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Daemon stopped by user")

    def _should_alert(self, key: str) -> bool:
        """Rate-limit duplicate alerts (1 per hour per key)."""
        if not self.notify_enabled:
            return False
        now = time.monotonic()
        last = self._last_alerts.get(key, 0)
        if now - last < self._cooldown:
            return False
        self._last_alerts[key] = now
        return True

    def _save_status(self, status: DaemonStatus) -> None:
        """Persist status to daemon_status.json."""
        try:
            STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATUS_FILE.write_text(
                json.dumps(status.to_dict(), indent=2, ensure_ascii=False)
            )
        except OSError as e:
            logger.error("Failed to save status: %s", e)

    @staticmethod
    def load_status() -> dict | None:
        """Load last daemon status from disk."""
        if not STATUS_FILE.exists():
            return None
        try:
            return json.loads(STATUS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return None

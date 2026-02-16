"""MoskvDaemon — Main daemon orchestrator."""

from __future__ import annotations

import json
import logging
import signal
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from cortex.daemon.models import (
    DaemonStatus,
    DEFAULT_INTERVAL, DEFAULT_STALE_HOURS, DEFAULT_MEMORY_STALE_HOURS,
    DEFAULT_COOLDOWN, DEFAULT_CERT_WARN_DAYS, DEFAULT_DISK_WARN_MB,
    CONFIG_FILE, STATUS_FILE, CORTEX_DB, CORTEX_DIR, AGENT_DIR,
)
from cortex.daemon.monitors import (
    SiteMonitor, GhostWatcher, MemorySyncer,
    CertMonitor, EngineHealthCheck, DiskMonitor,
)
from cortex.daemon.notifier import Notifier

import httpx

logger = logging.getLogger("moskv-daemon")


class MoskvDaemon:
    """MOSKV-1 persistent watchdog.

    Orchestrates all monitors and sends alerts.
    Configuration is loaded from ~/.cortex/daemon_config.json when present.

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
        cooldown: float = DEFAULT_COOLDOWN,
        notify: bool = True,
    ):
        self.notify_enabled = notify
        self.config_dir = config_dir
        self._shutdown = False

        file_config = self._load_config()
        resolved_sites = sites or file_config.get("sites", [])

        self.site_monitor = SiteMonitor(resolved_sites)
        self.ghost_watcher = GhostWatcher(
            config_dir / "ghosts.json",
            file_config.get("stale_hours", stale_hours),
        )
        self.memory_syncer = MemorySyncer(
            config_dir / "system.json",
            file_config.get("memory_stale_hours", memory_stale_hours),
        )

        cert_hostnames = [
            h.replace("https://", "").replace("http://", "").split("/")[0]
            for h in resolved_sites if h.startswith("https://")
        ]
        self.cert_monitor = CertMonitor(
            cert_hostnames,
            file_config.get("cert_warn_days", DEFAULT_CERT_WARN_DAYS),
        )
        self.engine_health = EngineHealthCheck(
            Path(file_config.get("db_path", str(CORTEX_DB)))
        )
        self.disk_monitor = DiskMonitor(
            Path(file_config.get("watch_path", str(CORTEX_DIR))),
            file_config.get("disk_warn_mb", DEFAULT_DISK_WARN_MB),
        )

        self._last_alerts: dict[str, float] = {}
        self._cooldown = file_config.get("cooldown", cooldown)

    @staticmethod
    def _load_config() -> dict:
        """Load daemon config from ~/.cortex/daemon_config.json if it exists."""
        if not CONFIG_FILE.exists():
            return {}
        try:
            return json.loads(CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load daemon config: %s", e)
            return {}

    def check(self) -> DaemonStatus:
        """Run all checks once. Returns DaemonStatus."""
        check_start = time.monotonic()
        now = datetime.now(timezone.utc).isoformat()
        status = DaemonStatus(checked_at=now)

        # 1. Site checks
        try:
            status.sites = self.site_monitor.check_all()
            for site in status.sites:
                if not site.healthy and self._should_alert(f"site:{site.url}"):
                    Notifier.alert_site_down(site)
        except (httpx.HTTPError, OSError) as e:
            status.errors.append(f"Site monitor error: {e}")
            logger.exception("Site monitor failed")

        # 2. Ghost checks
        try:
            status.stale_ghosts = self.ghost_watcher.check()
            for ghost in status.stale_ghosts:
                if self._should_alert(f"ghost:{ghost.project}"):
                    Notifier.alert_stale_project(ghost)
        except (json.JSONDecodeError, OSError, ValueError) as e:
            status.errors.append(f"Ghost watcher error: {e}")
            logger.exception("Ghost watcher failed")

        # 3. Memory checks
        try:
            status.memory_alerts = self.memory_syncer.check()
            for alert in status.memory_alerts:
                if self._should_alert(f"memory:{alert.file}"):
                    logger.warning("Memory file %s is stale, notification skipped", alert.file)
        except (json.JSONDecodeError, OSError, ValueError) as e:
            status.errors.append(f"Memory syncer error: {e}")
            logger.exception("Memory syncer failed")

        # 4. SSL certificate checks
        try:
            status.cert_alerts = self.cert_monitor.check()
            for cert in status.cert_alerts:
                if self._should_alert(f"cert:{cert.hostname}"):
                    logger.warning("SSL certificate for %s expiring soon", cert.hostname)
        except OSError as e:
            status.errors.append(f"Cert monitor error: {e}")
            logger.exception("Cert monitor failed")

        # 5. Engine health
        try:
            status.engine_alerts = self.engine_health.check()
            for eh in status.engine_alerts:
                if self._should_alert(f"engine:{eh.issue}"):
                    logger.warning("CORTEX Engine alert for %s", eh.issue)
        except OSError as e:
            status.errors.append(f"Engine health error: {e}")
            logger.exception("Engine health check failed")

        # 6. Disk usage
        try:
            status.disk_alerts = self.disk_monitor.check()
            for da in status.disk_alerts:
                if self._should_alert(f"disk:{da.path}"):
                    logger.warning("Disk space low on %s", da.path)
        except OSError as e:
            status.errors.append(f"Disk monitor error: {e}")
            logger.exception("Disk monitor failed")

        # 7. Automatic memory sync
        self._auto_sync(status)

        status.check_duration_ms = (time.monotonic() - check_start) * 1000
        self._save_status(status)

        level = "✅" if status.all_healthy else "⚠️"
        logger.info(
            "%s Check complete in %.0fms: %d sites, %d stale ghosts, %d memory alerts",
            level, status.check_duration_ms,
            len(status.sites), len(status.stale_ghosts), len(status.memory_alerts),
        )
        return status

    def _auto_sync(self, status: DaemonStatus) -> None:
        """Automatic memory JSON ↔ CORTEX DB synchronization."""
        try:
            from cortex.engine import CortexEngine
            from cortex.sync import sync_memory, export_snapshot, export_to_json
            engine = CortexEngine()
            engine.init_db()
            sync_result = sync_memory(engine)
            if sync_result.had_changes:
                logger.info("Sync automático: %d hechos sincronizados", sync_result.total)
            wb_result = export_to_json(engine)
            if wb_result.had_changes:
                logger.info("Write-back automático: %d archivos, %d items", wb_result.files_written, wb_result.items_exported)
            export_snapshot(engine)
            engine.close()
        except (sqlite3.Error, OSError, json.JSONDecodeError, ValueError) as e:
            status.errors.append(f"Memory sync error: {e}")
            logger.exception("Memory sync failed")

    def run(self, interval: int = DEFAULT_INTERVAL) -> None:
        """Run checks in a loop until stopped."""
        def _handle_signal(signum: int, frame: object) -> None:
            sig_name = signal.Signals(signum).name
            logger.info("Received %s, shutting down gracefully...", sig_name)
            self._shutdown = True

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

        logger.info("🚀 MOSKV-1 Daemon starting (interval=%ds)", interval)
        try:
            while not self._shutdown:
                self.check()
                for _ in range(interval):
                    if self._shutdown:
                        break
                    time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            logger.info("MOSKV-1 Daemon stopped")

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
            STATUS_FILE.write_text(json.dumps(status.to_dict(), indent=2, ensure_ascii=False))
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

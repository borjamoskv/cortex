"""MoskvDaemon — Main daemon orchestrator."""

from __future__ import annotations

import json
import logging
import signal
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import httpx

from cortex.daemon.models import (
    AGENT_DIR,
    CONFIG_FILE,
    CORTEX_DB,
    CORTEX_DIR,
    DEFAULT_CERT_WARN_DAYS,
    DEFAULT_COOLDOWN,
    DEFAULT_DISK_WARN_MB,
    DEFAULT_INTERVAL,
    DEFAULT_MEMORY_STALE_HOURS,
    DEFAULT_STALE_HOURS,
    STATUS_FILE,
    DaemonStatus,
)
from cortex.daemon.monitors import (
    AutonomousMejoraloMonitor,
    CertMonitor,
    DiskMonitor,
    EngineHealthCheck,
    GhostWatcher,
    MemorySyncer,
    SiteMonitor,
)
from cortex.daemon.notifier import Notifier

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
        self.auto_mejoralo = AutonomousMejoraloMonitor(
            projects=file_config.get("auto_mejoralo_projects", {}),
            interval_seconds=file_config.get("auto_mejoralo_interval", 1800),
        )

        cert_hostnames = [
            h.replace("https://", "").replace("http://", "").split("/")[0]
            for h in resolved_sites
            if h.startswith("https://")
        ]
        self.cert_monitor = CertMonitor(
            cert_hostnames,
            file_config.get("cert_warn_days", DEFAULT_CERT_WARN_DAYS),
        )
        self.engine_health = EngineHealthCheck(Path(file_config.get("db_path", str(CORTEX_DB))))
        self.disk_monitor = DiskMonitor(
            Path(file_config.get("watch_path", str(CORTEX_DIR))),
            file_config.get("disk_warn_mb", DEFAULT_DISK_WARN_MB),
        )

        self._last_alerts: dict[str, float] = {}
        self._cooldown = file_config.get("cooldown", cooldown)

        # Time Tracker (for flushing heartbeats)
        try:
            from cortex.timing import TimingTracker

            self.timing_conn = sqlite3.connect(file_config.get("db_path", str(CORTEX_DB)))
            self.tracker = TimingTracker(self.timing_conn)
        except (ImportError, sqlite3.Error) as e:
            logger.error("Failed to init TimeTracker: %s", e)
            self.tracker = None

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

        # Run all monitors through unified runner
        self._run_monitor(status, "sites", self.site_monitor, self._alert_sites, method="check_all")
        self._run_monitor(status, "stale_ghosts", self.ghost_watcher, self._alert_ghosts)
        self._run_monitor(status, "memory_alerts", self.memory_syncer, self._alert_memory)
        self._run_monitor(status, "cert_alerts", self.cert_monitor, self._alert_certs)
        self._run_monitor(status, "engine_alerts", self.engine_health, self._alert_engine)
        self._run_monitor(status, "disk_alerts", self.disk_monitor, self._alert_disk)
        self._run_monitor(status, "mejoralo_alerts", self.auto_mejoralo, self._alert_mejoralo)

        self._auto_sync(status)
        self._flush_timer()

        status.check_duration_ms = (time.monotonic() - check_start) * 1000
        self._save_status(status)

        level = "✅" if status.all_healthy else "⚠️"
        logger.info(
            "%s Check complete in %.0fms: %d sites, %d stale ghosts, %d memory alerts",
            level,
            status.check_duration_ms,
            len(status.sites),
            len(status.stale_ghosts),
            len(status.memory_alerts),
        )
        return status

    def _run_monitor(
        self,
        status: DaemonStatus,
        attr: str,
        monitor: object,
        alert_fn: Callable,
        method: str = "check",
    ) -> None:
        """Run a single monitor, store results, and fire alerts."""
        try:
            results = getattr(monitor, method)()
            if isinstance(results, list):
                setattr(status, attr, results)
            alert_fn(results)
        except (httpx.HTTPError, OSError, ValueError, sqlite3.Error) as e:
            status.errors.append(f"{type(monitor).__name__} error: {e}")
            logger.exception("%s failed", type(monitor).__name__)

    def _alert_sites(self, sites: list) -> None:
        for site in sites:
            if not site.healthy and self._should_alert(f"site:{site.url}"):
                Notifier.alert_site_down(site)

    def _alert_ghosts(self, ghosts: list) -> None:
        for ghost in ghosts:
            if self._should_alert(f"ghost:{ghost.project}"):
                Notifier.alert_stale_project(ghost)

    def _alert_memory(self, alerts: list) -> None:
        for alert in alerts:
            if self._should_alert(f"memory:{alert.file}"):
                logger.warning("Memory file %s is stale", alert.file)

    def _alert_certs(self, certs: list) -> None:
        for cert in certs:
            if self._should_alert(f"cert:{cert.hostname}"):
                logger.warning("SSL certificate for %s expiring soon", cert.hostname)

    def _alert_engine(self, alerts: list) -> None:
        for eh in alerts:
            if self._should_alert(f"engine:{eh.issue}"):
                logger.warning("CORTEX Engine alert for %s", eh.issue)

    def _alert_disk(self, alerts: list) -> None:
        for da in alerts:
            if self._should_alert(f"disk:{da.path}"):
                logger.warning("Disk space low on %s", da.path)

    def _alert_mejoralo(self, alerts: list) -> None:
        for alert in alerts:
            if alert.score < 50 and self._should_alert(f"mejoralo:{alert.project}"):
                logger.warning("Autonomous MEJORAlo scan for %s returned low score: %d/100 (Dead Code: %s)", 
                             alert.project, alert.score, alert.dead_code)
                try:
                    import subprocess
                    from cortex.daemon.notifier import Notifier
                    Notifier.notify(
                        "☢️ MEJORAlo Brutal Mode",
                        f"Project {alert.project} score: {alert.score}. Waking up Legion-1 Swarm (400-subagents).",
                        sound="Basso"
                    )
                    path_str = self.auto_mejoralo.projects.get(alert.project, ".")
                    # Dispatch en background (fire and forget)
                    subprocess.Popen(
                        [
                            "/Users/borjafernandezangulo/cortex/.venv/bin/python",
                            "-m", "cortex.cli", "mejoralo", "scan",
                            alert.project, ".", "--deep"
                        ],
                        cwd=path_str,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except Exception as e:
                    logger.error("Failed to auto-dispatch Swarm for %s: %s", alert.project, e)

    def _flush_timer(self) -> None:
        """Flush accumulated time tracker heartbeats."""
        if not self.tracker:
            return
        try:
            entries = self.tracker.flush()
            if entries > 0:
                logger.info("TimeTracker: Consolidado %d entradas de tiempo.", entries)
        except sqlite3.Error as e:
            logger.error("TimeTracker flush error: %s", e)

    def _auto_sync(self, status: DaemonStatus) -> None:
        """Automatic memory JSON ↔ CORTEX DB synchronization."""
        try:
            from cortex.engine import CortexEngine
            from cortex.sync import export_snapshot, export_to_json, sync_memory

            engine = CortexEngine()
            engine.init_db_sync()
            sync_result = sync_memory(engine)
            if sync_result.had_changes:
                logger.info("Sync automático: %d hechos sincronizados", sync_result.total)
            wb_result = export_to_json(engine)
            if wb_result.had_changes:
                logger.info(
                    "Write-back automático: %d archivos, %d items",
                    wb_result.files_written,
                    wb_result.items_exported,
                )
            import asyncio
            asyncio.run(export_snapshot(engine))
            engine.close_sync()

        except (sqlite3.Error, OSError, ValueError) as e:
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

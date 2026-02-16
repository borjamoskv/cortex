"""Daemon data classes and constants."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ─── Constants ────────────────────────────────────────────────────────

DEFAULT_INTERVAL = 300  # 5 minutes
DEFAULT_STALE_HOURS = 48  # ghost projects stale after 48h
DEFAULT_MEMORY_STALE_HOURS = 24  # system.json stale after 24h
DEFAULT_TIMEOUT = 10  # HTTP timeout seconds
DEFAULT_COOLDOWN = 3600  # 1 hour between duplicate alerts
DEFAULT_RETRIES = 1  # HTTP retry count before declaring failure
RETRY_BACKOFF = 2.0  # seconds between retries
DEFAULT_CERT_WARN_DAYS = 14  # warn if SSL expires within 14 days
DEFAULT_DISK_WARN_MB = 500  # warn if cortex dir exceeds 500 MB
CORTEX_DIR = Path.home() / ".cortex"
CORTEX_DB = CORTEX_DIR / "cortex.db"
AGENT_DIR = Path.home() / ".agent"
CONFIG_FILE = CORTEX_DIR / "daemon_config.json"
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
class CertAlert:
    """SSL certificate expiry warning."""
    hostname: str
    expires_at: str
    days_remaining: int


@dataclass
class EngineHealthAlert:
    """CORTEX engine / database health issue."""
    issue: str
    detail: str = ""


@dataclass
class DiskAlert:
    """Disk usage warning for CORTEX data directory."""
    path: str
    size_mb: float
    threshold_mb: float


@dataclass
class DaemonStatus:
    """Full daemon check result — persisted to disk."""
    checked_at: str
    check_duration_ms: float = 0.0
    sites: list[SiteStatus] = field(default_factory=list)
    stale_ghosts: list[GhostAlert] = field(default_factory=list)
    memory_alerts: list[MemoryAlert] = field(default_factory=list)
    cert_alerts: list[CertAlert] = field(default_factory=list)
    engine_alerts: list[EngineHealthAlert] = field(default_factory=list)
    disk_alerts: list[DiskAlert] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def all_healthy(self) -> bool:
        return (
            all(s.healthy for s in self.sites)
            and len(self.stale_ghosts) == 0
            and len(self.memory_alerts) == 0
            and len(self.cert_alerts) == 0
            and len(self.engine_alerts) == 0
            and len(self.disk_alerts) == 0
            and len(self.errors) == 0
        )

    def to_dict(self) -> dict:
        return {
            "checked_at": self.checked_at,
            "check_duration_ms": round(self.check_duration_ms, 1),
            "all_healthy": self.all_healthy,
            "sites": [
                {
                    "url": s.url, "healthy": s.healthy,
                    "status_code": s.status_code,
                    "response_ms": round(s.response_ms, 1),
                    "error": s.error, "checked_at": s.checked_at,
                }
                for s in self.sites
            ],
            "stale_ghosts": [
                {
                    "project": g.project, "last_activity": g.last_activity,
                    "hours_stale": round(g.hours_stale, 1),
                    "mood": g.mood, "blocked_by": g.blocked_by,
                }
                for g in self.stale_ghosts
            ],
            "memory_alerts": [
                {"file": m.file, "last_updated": m.last_updated, "hours_stale": round(m.hours_stale, 1)}
                for m in self.memory_alerts
            ],
            "cert_alerts": [
                {"hostname": c.hostname, "expires_at": c.expires_at, "days_remaining": c.days_remaining}
                for c in self.cert_alerts
            ],
            "engine_alerts": [
                {"issue": e.issue, "detail": e.detail}
                for e in self.engine_alerts
            ],
            "disk_alerts": [
                {"path": d.path, "size_mb": round(d.size_mb, 1), "threshold_mb": d.threshold_mb}
                for d in self.disk_alerts
            ],
            "errors": self.errors,
        }

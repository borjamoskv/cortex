"""
CORTEX v4.0 — Context Collector.

Gathers ambient signals from multiple sources: database (facts, ghosts,
transactions, heartbeats), filesystem, and git log.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from cortex.context.signals import Signal
from cortex.temporal import now_iso

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger("cortex.context")

# ─── Weight Constants ────────────────────────────────────────────────
# Weights reflect how strongly each signal type indicates active context.
WEIGHT_RECENT_FACT = 0.9
WEIGHT_ACTIVE_GHOST = 0.85
WEIGHT_RECENT_TX = 0.7
WEIGHT_HEARTBEAT = 0.95
WEIGHT_FS_RECENT = 0.4
WEIGHT_GIT_COMMIT = 0.6


class ContextCollector:
    """Collects ambient contextual signals from multiple sources.

    Sources:
        - Database: recent facts, active ghosts, recent transactions, heartbeats
        - Filesystem: recently modified files in workspace
        - Git: recent commits
    """

    def __init__(
        self,
        conn: aiosqlite.Connection,
        max_signals: int = 20,
        workspace_dir: str | None = None,
        git_enabled: bool = True,
    ):
        self.conn = conn
        self.max_signals = max_signals
        self.workspace_dir = Path(workspace_dir) if workspace_dir else Path.home()
        self.git_enabled = git_enabled

    async def collect_all(self) -> list[Signal]:
        """Collect signals from all available sources."""
        signals: list[Signal] = []

        # Database signals (always available)
        signals.extend(await self._collect_recent_facts())
        signals.extend(await self._collect_active_ghosts())
        signals.extend(await self._collect_recent_transactions())
        signals.extend(await self._collect_heartbeats())

        # External signals (best-effort)
        signals.extend(self._collect_fs_recent())

        if self.git_enabled:
            signals.extend(self._collect_git_log())

        # Sort by weight descending + recency, cap at max
        signals.sort(key=lambda s: (s.weight, s.timestamp), reverse=True)
        return signals[: self.max_signals]

    # ─── Database Signals ────────────────────────────────────────────

    async def _collect_recent_facts(self, limit: int = 10) -> list[Signal]:
        """Collect the most recently stored/updated facts."""
        sql = """
            SELECT id, project, content, fact_type, updated_at
            FROM facts
            WHERE valid_until IS NULL
            ORDER BY updated_at DESC
            LIMIT ?
        """
        try:
            async with self.conn.execute(sql, (limit,)) as cursor:
                rows = await cursor.fetchall()
        except (sqlite3.Error, OSError, ValueError):
            logger.debug("Could not collect recent facts", exc_info=True)
            return []

        return [
            Signal(
                source="db:facts",
                signal_type="recent_fact",
                content=f"[{row[3]}] {row[2][:120]}",
                project=row[1],
                timestamp=row[4] or now_iso(),
                weight=WEIGHT_RECENT_FACT * _recency_decay(i, limit),
            )
            for i, row in enumerate(rows)
        ]

    async def _collect_active_ghosts(self, limit: int = 10) -> list[Signal]:
        """Collect unresolved ghosts (pending work items)."""
        sql = """
            SELECT id, project, reference, context, created_at
            FROM ghosts
            WHERE resolved_at IS NULL
            ORDER BY created_at DESC
            LIMIT ?
        """
        try:
            async with self.conn.execute(sql, (limit,)) as cursor:
                rows = await cursor.fetchall()
        except (sqlite3.Error, OSError, ValueError):
            logger.debug("Could not collect ghosts", exc_info=True)
            return []

        return [
            Signal(
                source="db:ghosts",
                signal_type="active_ghost",
                content=f"Ghost: {row[2]} — {(row[3] or '')[:100]}",
                project=row[1],
                timestamp=row[4] or now_iso(),
                weight=WEIGHT_ACTIVE_GHOST,
            )
            for i, row in enumerate(rows)
        ]

    async def _collect_recent_transactions(self, limit: int = 10) -> list[Signal]:
        """Collect recent ledger transactions."""
        sql = """
            SELECT id, project, action, detail, timestamp
            FROM transactions
            ORDER BY id DESC
            LIMIT ?
        """
        try:
            async with self.conn.execute(sql, (limit,)) as cursor:
                rows = await cursor.fetchall()
        except (sqlite3.Error, OSError, ValueError):
            logger.debug("Could not collect transactions", exc_info=True)
            return []

        signals = []
        for i, row in enumerate(rows):
            detail = ""
            if row[3]:
                try:
                    d = json.loads(row[3]) if isinstance(row[3], str) else row[3]
                    detail = f" — {d.get('content', '')[:80]}" if isinstance(d, dict) else ""
                except (json.JSONDecodeError, TypeError):
                    pass

            signals.append(
                Signal(
                    source="db:transactions",
                    signal_type="recent_tx",
                    content=f"[{row[2]}] {row[1]}{detail}",
                    project=row[1],
                    timestamp=row[4] or now_iso(),
                    weight=WEIGHT_RECENT_TX * _recency_decay(i, limit),
                )
            )
        return signals

    async def _collect_heartbeats(self, limit: int = 5) -> list[Signal]:
        """Collect recent heartbeat activity pulses."""
        sql = """
            SELECT id, project, entity, category, timestamp
            FROM heartbeats
            ORDER BY id DESC
            LIMIT ?
        """
        try:
            async with self.conn.execute(sql, (limit,)) as cursor:
                rows = await cursor.fetchall()
        except (sqlite3.Error, OSError, ValueError):
            logger.debug("Could not collect heartbeats", exc_info=True)
            return []

        return [
            Signal(
                source="db:heartbeats",
                signal_type="heartbeat",
                content=f"Active in {row[1]}: {row[2] or 'unknown entity'} ({row[3] or 'general'})",
                project=row[1],
                timestamp=row[4] or now_iso(),
                weight=WEIGHT_HEARTBEAT * _recency_decay(i, limit),
            )
            for i, row in enumerate(rows)
        ]

    # ─── External Signals ────────────────────────────────────────────

    def _collect_fs_recent(self, limit: int = 5) -> list[Signal]:
        """Collect recently modified files in workspace (best-effort)."""
        signals = []
        try:
            py_files = sorted(
                self.workspace_dir.rglob("*.py"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )[:limit]

            now_ts = datetime.now(tz=timezone.utc).timestamp()
            for i, f in enumerate(py_files):
                age_hours = (now_ts - f.stat().st_mtime) / 3600
                # Only include files modified in last 24h
                if age_hours > 24:
                    continue
                mod_time = datetime.fromtimestamp(
                    f.stat().st_mtime, tz=timezone.utc
                ).isoformat()
                signals.append(
                    Signal(
                        source="fs:recent",
                        signal_type="file_change",
                        content=f"Modified: {f.name} ({age_hours:.1f}h ago)",
                        project=_infer_project_from_path(f),
                        timestamp=mod_time,
                        weight=WEIGHT_FS_RECENT * _recency_decay(i, limit),
                    )
                )
        except (sqlite3.Error, OSError, ValueError):
            logger.debug("Could not scan filesystem", exc_info=True)

        return signals

    def _collect_git_log(self, limit: int = 5) -> list[Signal]:
        """Collect recent git commits (best-effort)."""
        signals = []
        try:
            result = subprocess.run(
                ["git", "log", f"--max-count={limit}", "--format=%H|%ai|%s"],
                capture_output=True,
                text=True,
                cwd=str(self.workspace_dir),
                timeout=5,
            )
            if result.returncode != 0:
                return []

            for i, line in enumerate(result.stdout.strip().split("\n")):
                if not line.strip():
                    continue
                parts = line.split("|", 2)
                if len(parts) < 3:
                    continue
                _, timestamp, message = parts
                signals.append(
                    Signal(
                        source="git:log",
                        signal_type="commit",
                        content=f"Commit: {message[:100]}",
                        project=_infer_project_from_path(self.workspace_dir),
                        timestamp=timestamp.strip(),
                        weight=WEIGHT_GIT_COMMIT * _recency_decay(i, limit),
                    )
                )
        except (sqlite3.Error, OSError, ValueError):
            logger.debug("Could not read git log", exc_info=True)

        return signals


# ─── Helpers ─────────────────────────────────────────────────────────


def _recency_decay(rank: int, total: int) -> float:
    """Linear decay: rank 0 = 1.0, rank total-1 = 0.5."""
    if total <= 1:
        return 1.0
    return 1.0 - 0.5 * (rank / (total - 1))


def _infer_project_from_path(path: Path) -> str | None:
    """Try to infer project name from directory structure."""
    try:
        parts = path.resolve().parts
        # Look for common project indicators
        for i, part in enumerate(parts):
            if part in ("projects", "src", "repos", "workspace"):
                if i + 1 < len(parts):
                    return parts[i + 1]
        # Fallback: use parent directory name
        if path.is_file():
            return path.parent.name
        return path.name
    except (sqlite3.Error, OSError, ValueError):
        return None

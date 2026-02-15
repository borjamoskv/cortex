"""
CORTEX v4.0 — Automatic Time Tracking.

Heartbeat-based developer time tracking. No manual timers.
Detects activity by periodic pulses and auto-classifies into
coding, docs, comms, testing, debugging, review, and other.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from cortex.temporal import now_iso

logger = logging.getLogger("cortex")

# ─── Activity Classification ─────────────────────────────────────────

CATEGORY_MAP: dict[str, str] = {
    # Coding
    ".py": "coding", ".js": "coding", ".ts": "coding", ".tsx": "coding",
    ".jsx": "coding", ".swift": "coding", ".rs": "coding", ".go": "coding",
    ".java": "coding", ".kt": "coding", ".c": "coding", ".cpp": "coding",
    ".h": "coding", ".rb": "coding", ".php": "coding", ".cs": "coding",
    ".css": "coding", ".scss": "coding", ".less": "coding",
    ".html": "coding", ".vue": "coding", ".svelte": "coding",
    ".sql": "coding", ".sh": "coding", ".bash": "coding",
    # Docs
    ".md": "docs", ".txt": "docs", ".rst": "docs", ".adoc": "docs",
    ".pdf": "docs", ".doc": "docs", ".docx": "docs",
    # Config
    ".json": "coding", ".yaml": "coding", ".yml": "coding",
    ".toml": "coding", ".ini": "coding", ".env": "coding",
}

ENTITY_KEYWORDS: dict[str, str] = {
    "test_": "testing", "_test.": "testing", ".test.": "testing",
    ".spec.": "testing", "spec_": "testing",
    "slack": "comms", "discord": "comms", "teams": "comms",
    "outlook": "comms", "gmail": "comms", "mail": "comms",
    "zoom": "comms", "meet": "comms",
    "debug": "debugging", "debugger": "debugging",
    "review": "review", "pr": "review", "diff": "review",
    "docs.": "docs", "stackoverflow": "docs", "mdn": "docs",
}

# Default gap threshold: heartbeats > 5 min apart = different sessions
DEFAULT_GAP_SECONDS = 300


def classify_entity(entity: str) -> str:
    """Auto-classify an entity (file/url/app) into an activity category."""
    if not entity:
        return "other"

    entity_lower = entity.lower()

    # Check keyword matches first (more specific)
    for keyword, category in ENTITY_KEYWORDS.items():
        if keyword in entity_lower:
            return category

    # Check file extension
    ext = os.path.splitext(entity_lower)[1]
    if ext in CATEGORY_MAP:
        return CATEGORY_MAP[ext]

    return "other"


# ─── Data Classes ─────────────────────────────────────────────────────


@dataclass
class Heartbeat:
    """A single activity pulse."""
    id: int
    project: str
    entity: str
    category: str
    branch: Optional[str]
    language: Optional[str]
    timestamp: str
    meta: dict


@dataclass
class TimeEntry:
    """A continuous block of activity."""
    id: int
    project: str
    category: str
    start_time: str
    end_time: str
    duration_s: int
    entities: list[str]
    heartbeats: int
    meta: dict


@dataclass
class TimeSummary:
    """Aggregated time report."""
    total_seconds: int
    by_category: dict[str, int]
    by_project: dict[str, int]
    entries: int
    heartbeats: int
    top_entities: list[tuple[str, int]]  # (entity, count)

    @property
    def total_hours(self) -> float:
        return round(self.total_seconds / 3600, 2)

    def format_duration(self, seconds: int) -> str:
        """Format seconds as 'Xh Ym'."""
        h, m = divmod(seconds // 60, 60)
        if h > 0:
            return f"{h}h {m}m"
        return f"{m}m"


# ─── Timing Tracker ───────────────────────────────────────────────────


class TimingTracker:
    """Automatic time tracker using heartbeats.

    Usage:
        tracker = TimingTracker(conn)
        tracker.heartbeat("naroa-web", "css/variables.css")
        tracker.heartbeat("naroa-web", "js/app.js")
        tracker.flush()  # Groups heartbeats into time entries
        summary = tracker.today()
    """

    def __init__(self, conn: sqlite3.Connection, gap_seconds: int = DEFAULT_GAP_SECONDS):
        self._conn = conn
        self._gap_seconds = gap_seconds

    def heartbeat(
        self,
        project: str,
        entity: str = "",
        category: str | None = None,
        branch: str | None = None,
        language: str | None = None,
        timestamp: str | None = None,
        meta: dict | None = None,
    ) -> int:
        """Record a single activity heartbeat.

        Args:
            project: Project identifier.
            entity: Active file, URL, or app name.
            category: Activity type. Auto-classified if None.
            branch: Git branch (optional).
            language: Programming language (optional).
            timestamp: ISO 8601. Defaults to now.
            meta: Additional metadata.

        Returns:
            Heartbeat ID.
        """
        ts = timestamp or now_iso()
        cat = category or classify_entity(entity)
        meta_json = json.dumps(meta or {})

        cursor = self._conn.execute(
            """
            INSERT INTO heartbeats (project, entity, category, branch, language, timestamp, meta)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (project, entity, cat, branch, language, ts, meta_json),
        )
        self._conn.commit()
        logger.debug(f"Heartbeat: {project}/{entity} [{cat}]")
        return cursor.lastrowid

    def flush(self, gap_seconds: int | None = None) -> int:
        """Group unflushed heartbeats into continuous time entries.

        Heartbeats within `gap_seconds` of each other are merged into
        a single time entry.

        Returns:
            Number of time entries created.
        """
        gap = gap_seconds or self._gap_seconds

        # Get all heartbeats not yet assigned to a time entry
        # We track which heartbeats have been flushed by checking
        # if their timestamp is after the latest time_entry end_time
        latest_end = self._conn.execute(
            "SELECT MAX(end_time) FROM time_entries"
        ).fetchone()[0]

        if latest_end:
            rows = self._conn.execute(
                """
                SELECT id, project, entity, category, timestamp
                FROM heartbeats
                WHERE timestamp > ?
                ORDER BY timestamp ASC
                """,
                (latest_end,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id, project, entity, category, timestamp
                FROM heartbeats
                ORDER BY timestamp ASC
                """
            ).fetchall()

        if not rows:
            return 0

        # Group into entries by project+category with gap detection
        entries_created = 0
        current_group: list[tuple] = [rows[0]]

        for row in rows[1:]:
            prev_ts = datetime.fromisoformat(current_group[-1][4])
            curr_ts = datetime.fromisoformat(row[4])
            same_context = (
                row[1] == current_group[0][1]  # same project
                and row[3] == current_group[0][3]  # same category
            )
            within_gap = (curr_ts - prev_ts).total_seconds() <= gap

            if same_context and within_gap:
                current_group.append(row)
            else:
                entries_created += self._save_entry(current_group)
                current_group = [row]

        # Save last group
        entries_created += self._save_entry(current_group)
        return entries_created

    def _save_entry(self, group: list[tuple]) -> int:
        """Save a group of heartbeats as a time entry."""
        if not group:
            return 0

        project = group[0][1]
        category = group[0][3]
        start_time = group[0][4]
        end_time = group[-1][4]

        # Duration: at least 1 heartbeat interval, minimum 30s per heartbeat
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        duration_s = max(int((end_dt - start_dt).total_seconds()), 30)

        entities = list({row[2] for row in group if row[2]})
        entities_json = json.dumps(entities)

        self._conn.execute(
            """
            INSERT INTO time_entries
                (project, category, start_time, end_time, duration_s, entities, heartbeats, meta)
            VALUES (?, ?, ?, ?, ?, ?, ?, '{}')
            """,
            (project, category, start_time, end_time, duration_s, entities_json, len(group)),
        )
        self._conn.commit()
        return 1

    def today(self, project: str | None = None) -> TimeSummary:
        """Get time summary for today.

        Args:
            project: Optional project filter.

        Returns:
            TimeSummary with today's aggregated data.
        """
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self._summarize(f"{today_str}%", project)

    def report(
        self,
        project: str | None = None,
        days: int = 7,
    ) -> TimeSummary:
        """Get time report for the last N days.

        Args:
            project: Optional project filter.
            days: Number of days to include.

        Returns:
            TimeSummary for the period.
        """
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        where = ["start_time >= ?"]
        params: list = [cutoff]

        if project:
            where.append("project = ?")
            params.append(project)

        where_clause = " AND ".join(where)

        return self._build_summary(where_clause, params)

    def timeline(
        self,
        project: str | None = None,
        date: str | None = None,
    ) -> list[TimeEntry]:
        """Get detailed timeline for a date.

        Args:
            project: Optional project filter.
            date: Date string (YYYY-MM-DD). Defaults to today.

        Returns:
            List of TimeEntry objects ordered chronologically.
        """
        date_str = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        where = ["start_time LIKE ?"]
        params: list = [f"{date_str}%"]

        if project:
            where.append("project = ?")
            params.append(project)

        where_clause = " AND ".join(where)

        rows = self._conn.execute(
            f"""
            SELECT id, project, category, start_time, end_time,
                   duration_s, entities, heartbeats, meta
            FROM time_entries
            WHERE {where_clause}
            ORDER BY start_time ASC
            """,
            params,
        ).fetchall()

        return [
            TimeEntry(
                id=r[0], project=r[1], category=r[2],
                start_time=r[3], end_time=r[4],
                duration_s=r[5],
                entities=json.loads(r[6]) if r[6] else [],
                heartbeats=r[7],
                meta=json.loads(r[8]) if r[8] else {},
            )
            for r in rows
        ]

    def daily(self, days: int = 7) -> list[dict]:
        """Get total seconds per day for the last N days.

        Args:
            days: Number of days to include.

        Returns:
            List of dicts: {"date": "YYYY-MM-DD", "seconds": 3600}
        """
        from datetime import timedelta
        
        # Init map with 0s for all dates
        end_date = datetime.now(timezone.utc).date()
        date_map = {}
        for i in range(days):
            d = (end_date - timedelta(days=i)).isoformat()
            date_map[d] = 0
            
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        rows = self._conn.execute(
            """
            SELECT substr(start_time, 1, 10) as date, SUM(duration_s)
            FROM time_entries
            WHERE start_time >= ?
            GROUP BY date
            """,
            (cutoff,)
        ).fetchall()
        
        for r in rows:
            if r[0] in date_map:
                date_map[r[0]] = r[1]
                
        # Return sorted list
        return [
            {"date": d, "seconds": date_map[d]} 
            for d in sorted(date_map.keys())
        ]

    # ─── Internal Helpers ─────────────────────────────────────────

    def _summarize(self, date_pattern: str, project: str | None) -> TimeSummary:
        """Build summary for entries matching a date pattern."""
        where = ["start_time LIKE ?"]
        params: list = [date_pattern]

        if project:
            where.append("project = ?")
            params.append(project)

        return self._build_summary(" AND ".join(where), params)

    def _build_summary(self, where_clause: str, params: list) -> TimeSummary:
        """Build a TimeSummary from a WHERE clause."""
        rows = self._conn.execute(
            f"""
            SELECT project, category, duration_s, entities, heartbeats
            FROM time_entries
            WHERE {where_clause}
            """,
            params,
        ).fetchall()

        total_seconds = 0
        by_category: dict[str, int] = {}
        by_project: dict[str, int] = {}
        entity_counts: dict[str, int] = {}
        total_heartbeats = 0
        entries = len(rows)

        for row in rows:
            proj, cat, dur, ents_json, hb = row
            total_seconds += dur
            by_category[cat] = by_category.get(cat, 0) + dur
            by_project[proj] = by_project.get(proj, 0) + dur
            total_heartbeats += hb

            for entity in json.loads(ents_json or "[]"):
                entity_counts[entity] = entity_counts.get(entity, 0) + 1

        top_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return TimeSummary(
            total_seconds=total_seconds,
            by_category=by_category,
            by_project=by_project,
            entries=entries,
            heartbeats=total_heartbeats,
            top_entities=top_entities,
        )

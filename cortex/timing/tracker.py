"""TimingTracker — heartbeat-based time tracking."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta, timezone

from cortex.temporal import now_iso
from cortex.timing.models import (
    TimeEntry, TimeSummary, DEFAULT_GAP_SECONDS, classify_entity,
)

logger = logging.getLogger("cortex")


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
        self._lock = threading.Lock()

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
        """Record a single activity heartbeat. Returns Heartbeat ID."""
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
        logger.debug("Heartbeat: %s/%s [%s]", project, entity, cat)
        return cursor.lastrowid

    def flush(self, gap_seconds: int | None = None) -> int:
        """Group unflushed heartbeats into continuous time entries.

        Returns:
            Number of time entries created.
        """
        with self._lock:
            gap = gap_seconds or self._gap_seconds

        latest_end = self._conn.execute(
            "SELECT MAX(end_time) FROM time_entries"
        ).fetchone()[0]

        if latest_end:
            rows = self._conn.execute(
                "SELECT id, project, entity, category, timestamp "
                "FROM heartbeats WHERE timestamp > ? ORDER BY timestamp ASC",
                (latest_end,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, project, entity, category, timestamp "
                "FROM heartbeats ORDER BY timestamp ASC"
            ).fetchall()

        if not rows:
            return 0

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
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        duration_s = max(int((end_dt - start_dt).total_seconds()), 30)
        entities = list({row[2] for row in group if row[2]})
        entities_json = json.dumps(entities)
        self._conn.execute(
            "INSERT INTO time_entries "
            "(project, category, start_time, end_time, duration_s, entities, heartbeats, meta) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, '{}')",
            (project, category, start_time, end_time, duration_s, entities_json, len(group)),
        )
        self._conn.commit()
        return 1

    def today(self, project: str | None = None) -> TimeSummary:
        """Get time summary for today."""
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self._summarize(f"{today_str}%", project)

    def report(self, project: str | None = None, days: int = 7) -> TimeSummary:
        """Get time report for the last N days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        where = ["start_time >= ?"]
        params: list = [cutoff]
        if project:
            where.append("project = ?")
            params.append(project)
        return self._build_summary(" AND ".join(where), params)

    def timeline(self, project: str | None = None, date: str | None = None) -> list[TimeEntry]:
        """Get detailed timeline for a date."""
        date_str = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        where = ["start_time LIKE ?"]
        params: list = [f"{date_str}%"]
        if project:
            where.append("project = ?")
            params.append(project)
        where_clause = " AND ".join(where)
        rows = self._conn.execute(
            f"SELECT id, project, category, start_time, end_time, "
            f"duration_s, entities, heartbeats, meta "
            f"FROM time_entries WHERE {where_clause} ORDER BY start_time ASC",
            params,
        ).fetchall()
        return [
            TimeEntry(
                id=r[0], project=r[1], category=r[2],
                start_time=r[3], end_time=r[4], duration_s=r[5],
                entities=json.loads(r[6]) if r[6] else [],
                heartbeats=r[7],
                meta=json.loads(r[8]) if r[8] else {},
            )
            for r in rows
        ]

    def daily(self, days: int = 7) -> list[dict]:
        """Get total seconds per day for the last N days."""
        end_date = datetime.now(timezone.utc).date()
        date_map = {}
        for i in range(days):
            d = (end_date - timedelta(days=i)).isoformat()
            date_map[d] = 0
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = self._conn.execute(
            "SELECT substr(start_time, 1, 10) as date, SUM(duration_s) "
            "FROM time_entries WHERE start_time >= ? GROUP BY date",
            (cutoff,)
        ).fetchall()
        for r in rows:
            if r[0] in date_map:
                date_map[r[0]] = r[1]
        return [{"date": d, "seconds": date_map[d]} for d in sorted(date_map.keys())]

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
            f"SELECT project, category, duration_s, entities, heartbeats "
            f"FROM time_entries WHERE {where_clause}",
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
            total_seconds=total_seconds, by_category=by_category,
            by_project=by_project, entries=entries,
            heartbeats=total_heartbeats, top_entities=top_entities,
        )

    def _safe_json_list(self, val) -> list:
        """Safely decode JSON list, returning [] on failure."""
        if not val:
            return []
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def _safe_json_dict(self, val) -> dict:
        """Safely decode JSON dict, returning {} on failure."""
        if not val:
            return {}
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

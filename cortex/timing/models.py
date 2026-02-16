"""Timing data classes, constants, and classification."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


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

DEFAULT_GAP_SECONDS = 300


def classify_entity(entity: str) -> str:
    """Auto-classify an entity (file/url/app) into an activity category."""
    if not entity:
        return "other"
    entity_lower = entity.lower()
    for keyword, category in ENTITY_KEYWORDS.items():
        if keyword in entity_lower:
            return category
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
    top_entities: list[tuple[str, int]]

    @property
    def total_hours(self) -> float:
        return round(self.total_seconds / 3600, 2)

    def format_duration(self, seconds: int) -> str:
        """Format seconds as 'Xh Ym'."""
        h, m = divmod(seconds // 60, 60)
        if h > 0:
            return f"{h}h {m}m"
        return f"{m}m"

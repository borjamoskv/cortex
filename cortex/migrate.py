"""
CORTEX v4.0 — Migration from v3.1 (JSON) to v4.0 (SQLite).

Reads v3.1 files (system.json, projects/*.json, mistakes.jsonl, bridges.jsonl)
and imports them into the v4.0 database. Non-destructive: never modifies source files.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.migrate")


def migrate_v31_to_v40(
    engine: CortexEngine,
    source_dir: str = "~/.agent/memory",
) -> dict:
    """Migrate CORTEX v3.1 JSON data to v4.0 SQLite.

    Args:
        engine: Initialized CortexEngine.
        source_dir: Path to v3.1 memory directory.

    Returns:
        Migration statistics dict.
    """
    src = Path(source_dir).expanduser()
    stats = {
        "facts_imported": 0,
        "errors_imported": 0,
        "bridges_imported": 0,
        "sessions_imported": 0,
        "skipped": 0,
        "errors": [],
    }

    if not src.exists():
        logger.warning(f"Source directory not found: {src}")
        stats["errors"].append(f"Source not found: {src}")
        return stats

    # 1. Migrate system.json
    system_file = src / "system.json"
    if system_file.exists():
        _migrate_system(engine, system_file, stats)

    # 2. Migrate project files
    projects_dir = src / "projects"
    if projects_dir.exists():
        for pfile in projects_dir.glob("*.json"):
            _migrate_project(engine, pfile, stats)

    # 3. Migrate mistakes.jsonl
    mistakes_file = src / "mistakes.jsonl"
    if mistakes_file.exists():
        _migrate_mistakes(engine, mistakes_file, stats)

    # 4. Migrate bridges.jsonl
    bridges_file = src / "bridges.jsonl"
    if bridges_file.exists():
        _migrate_bridges(engine, bridges_file, stats)

    logger.info(f"Migration complete: {stats}")
    return stats


def _migrate_system(engine: CortexEngine, path: Path, stats: dict) -> None:
    """Migrate system.json — preferences, decisions, knowledge, sessions."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        stats["errors"].append(f"Failed to read system.json: {e}")
        return

    project = "__system__"

    # Preferences
    prefs = data.get("preferences", {})
    if prefs:
        engine.store(
            project=project,
            content=json.dumps(prefs, ensure_ascii=False),
            fact_type="preference",
            tags=["system", "preferences"],
            confidence="verified",
            source="migration-v3.1",
        )
        stats["facts_imported"] += 1

    # Operator info
    operator = data.get("operator", {})
    if operator:
        engine.store(
            project=project,
            content=json.dumps(operator, ensure_ascii=False),
            fact_type="identity",
            tags=["system", "operator"],
            confidence="verified",
            source="migration-v3.1",
        )
        stats["facts_imported"] += 1

    # Global decisions
    for decision in data.get("global_decisions", []):
        engine.store(
            project=project,
            content=decision.get("decision", str(decision)),
            fact_type="decision",
            tags=["system", "global"],
            confidence="verified",
            source="migration-v3.1",
            meta=decision,
        )
        stats["facts_imported"] += 1

    # Knowledge items
    for ki in data.get("knowledge", []):
        engine.store(
            project=project,
            content=ki.get("content", str(ki)),
            fact_type="knowledge",
            tags=["system", ki.get("topic", "general")],
            confidence=ki.get("confidence", "stated"),
            source="migration-v3.1",
            valid_from=ki.get("added", None),
            meta=ki,
        )
        stats["facts_imported"] += 1

    # Sessions
    conn = engine._get_conn()
    for session in data.get("sessions_log", []):
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO sessions (id, date, focus, summary, conversations)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session.get("id", f"S{session.get('date', 'unknown')}"),
                    session.get("date", ""),
                    json.dumps(session.get("focus", [])),
                    session.get("summary", ""),
                    session.get("conversations", 1),
                ),
            )
            stats["sessions_imported"] += 1
        except Exception as e:
            stats["errors"].append(f"Session import failed: {e}")

    conn.commit()


def _migrate_project(engine: CortexEngine, path: Path, stats: dict) -> None:
    """Migrate a single project JSON file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        stats["errors"].append(f"Failed to read {path.name}: {e}")
        return

    project = data.get("meta", {}).get("id", path.stem)

    # Decisions
    for decision in data.get("decisions", []):
        engine.store(
            project=project,
            content=decision.get("decision", str(decision)),
            fact_type="decision",
            tags=decision.get("tags", []),
            confidence="verified",
            source="migration-v3.1",
            meta=decision,
        )
        stats["facts_imported"] += 1

    # Knowledge
    for ki in data.get("knowledge", []):
        engine.store(
            project=project,
            content=ki.get("content", str(ki)),
            fact_type="knowledge",
            tags=[ki.get("type", "factual")],
            confidence=ki.get("confidence", "stated"),
            source="migration-v3.1",
            meta=ki,
        )
        stats["facts_imported"] += 1

    # Known issues
    for issue in data.get("known_issues", []):
        engine.store(
            project=project,
            content=issue if isinstance(issue, str) else str(issue),
            fact_type="issue",
            tags=["known-issue"],
            source="migration-v3.1",
        )
        stats["facts_imported"] += 1

    # Ghost (last state)
    ghost = data.get("ghost", {})
    if ghost:
        engine.store(
            project=project,
            content=json.dumps(ghost, ensure_ascii=False),
            fact_type="ghost",
            tags=["context", "last-state"],
            source="migration-v3.1",
            meta=ghost,
        )
        stats["facts_imported"] += 1


def _migrate_mistakes(engine: CortexEngine, path: Path, stats: dict) -> None:
    """Migrate mistakes.jsonl — error memory."""
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        try:
            mistake = json.loads(line)
            project = mistake.get("project", "__system__")

            content = (
                f"ERROR: {mistake.get('error', 'unknown')} | "
                f"ROOT CAUSE: {mistake.get('root_cause', 'unknown')} | "
                f"FIX: {mistake.get('fix', 'unknown')}"
            )

            engine.store(
                project=project,
                content=content,
                fact_type="error",
                tags=mistake.get("tags", []),
                confidence="verified",
                source="migration-v3.1",
                valid_from=mistake.get("date", None),
                meta=mistake,
            )
            stats["errors_imported"] += 1
        except Exception as e:
            stats["errors"].append(f"Mistake import failed: {e}")


def _migrate_bridges(engine: CortexEngine, path: Path, stats: dict) -> None:
    """Migrate bridges.jsonl — cross-project connections."""
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        try:
            bridge = json.loads(line)

            content = (
                f"BRIDGE: {bridge.get('from', '?')} → {bridge.get('to', '?')} | "
                f"Pattern: {bridge.get('pattern', '?')} | "
                f"Note: {bridge.get('note', '')}"
            )

            engine.store(
                project="__bridges__",
                content=content,
                fact_type="bridge",
                tags=[bridge.get("from", ""), bridge.get("to", ""), bridge.get("pattern", "")],
                confidence="verified",
                source="migration-v3.1",
                valid_from=bridge.get("date", None),
                meta=bridge,
            )
            stats["bridges_imported"] += 1
        except Exception as e:
            stats["errors"].append(f"Bridge import failed: {e}")

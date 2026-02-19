"""
CORTEX v4.0 — Session Handoff Protocol.

Generates a compact, relevance-ranked handoff for seamless session continuity.
Instead of dumping all facts (snapshot), the handoff captures only the hot context:
recent decisions, active ghosts, recent errors, and session metadata.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cortex.sync.common import CORTEX_DIR, atomic_write
from cortex.temporal import now_iso

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.handoff")

HANDOFF_VERSION = "1.0"
DEFAULT_HANDOFF_PATH = CORTEX_DIR / "handoff.json"

# Limits
MAX_DECISIONS = 10
MAX_ERRORS = 5
MAX_GHOSTS = 20


async def generate_handoff(
    engine: CortexEngine,
    session_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a compact handoff from current CORTEX state.

    Args:
        engine: Active CortexEngine instance.
        session_meta: Optional session metadata (focus_projects, pending_work, mood).

    Returns:
        Handoff dictionary ready for serialization.
    """
    conn = await engine.get_conn()

    # ── Hot Decisions (last N, ordered by recency) ────────────────────
    async with conn.execute(
        "SELECT id, project, content, created_at "
        "FROM facts "
        "WHERE fact_type = 'decision' AND valid_until IS NULL "
        "ORDER BY created_at DESC LIMIT ?",
        (MAX_DECISIONS,),
    ) as cursor:
        decision_rows = await cursor.fetchall()

    hot_decisions = [
        {"id": r[0], "project": r[1], "content": r[2], "created_at": r[3]}
        for r in decision_rows
    ]

    # ── Active Ghosts ─────────────────────────────────────────────────
    async with conn.execute(
        "SELECT id, project, reference, context "
        "FROM ghosts "
        "WHERE status = 'open' "
        "ORDER BY created_at DESC LIMIT ?",
        (MAX_GHOSTS,),
    ) as cursor:
        ghost_rows = await cursor.fetchall()

    active_ghosts = [
        {"id": r[0], "project": r[1], "reference": r[2], "context": r[3]}
        for r in ghost_rows
    ]

    # ── Recent Errors ─────────────────────────────────────────────────
    async with conn.execute(
        "SELECT id, project, content, created_at "
        "FROM facts "
        "WHERE fact_type IN ('error', 'mistake') AND valid_until IS NULL "
        "ORDER BY created_at DESC LIMIT ?",
        (MAX_ERRORS,),
    ) as cursor:
        error_rows = await cursor.fetchall()

    recent_errors = [
        {"id": r[0], "project": r[1], "content": r[2], "created_at": r[3]}
        for r in error_rows
    ]

    # ── Active Projects (with activity in last 24h) ───────────────────
    async with conn.execute(
        "SELECT DISTINCT project FROM facts "
        "WHERE created_at >= datetime('now', '-1 day') "
        "AND valid_until IS NULL "
        "ORDER BY project"
    ) as cursor:
        project_rows = await cursor.fetchall()

    active_projects = [r[0] for r in project_rows]

    # ── Stats summary ─────────────────────────────────────────────────
    async with conn.execute(
        "SELECT COUNT(*) FROM facts WHERE valid_until IS NULL"
    ) as cursor:
        total_active = (await cursor.fetchone())[0]

    async with conn.execute(
        "SELECT COUNT(DISTINCT project) FROM facts WHERE valid_until IS NULL"
    ) as cursor:
        total_projects = (await cursor.fetchone())[0]

    db_path = Path(engine._db_path)
    db_size_mb = round(db_path.stat().st_size / (1024 * 1024), 2) if db_path.exists() else 0.0

    # ── Session metadata (from caller) ────────────────────────────────
    session = {
        "focus_projects": [],
        "pending_work": [],
        "mood": "neutral",
    }
    if session_meta:
        session.update(session_meta)

    handoff = {
        "version": HANDOFF_VERSION,
        "generated_at": now_iso(),
        "session": session,
        "hot_decisions": hot_decisions,
        "active_ghosts": active_ghosts,
        "recent_errors": recent_errors,
        "active_projects": active_projects,
        "stats": {
            "total_facts": total_active,
            "total_projects": total_projects,
            "db_size_mb": db_size_mb,
        },
    }

    logger.info(
        "Handoff generated: %d decisions, %d ghosts, %d errors, %d active projects",
        len(hot_decisions),
        len(active_ghosts),
        len(recent_errors),
        len(active_projects),
    )

    return handoff


def save_handoff(
    handoff_data: dict[str, Any],
    path: Path | None = None,
) -> Path:
    """Atomically save handoff JSON to disk.

    Args:
        handoff_data: The handoff dictionary.
        path: Output path. Defaults to ~/.cortex/handoff.json

    Returns:
        Path where the handoff was saved.
    """
    out_path = path or DEFAULT_HANDOFF_PATH
    content = json.dumps(handoff_data, indent=2, ensure_ascii=False)
    atomic_write(out_path, content)
    logger.info("Handoff saved to %s", out_path)
    return out_path


def load_handoff(path: Path | None = None) -> dict[str, Any] | None:
    """Load an existing handoff from disk.

    Args:
        path: Path to handoff.json. Defaults to ~/.cortex/handoff.json

    Returns:
        Parsed handoff dict, or None if not found / corrupt.
    """
    target = path or DEFAULT_HANDOFF_PATH
    if not target.exists():
        logger.warning("No handoff found at %s", target)
        return None

    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        logger.info("Handoff loaded from %s (v%s)", target, data.get("version", "?"))
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load handoff from %s: %s", target, e)
        return None

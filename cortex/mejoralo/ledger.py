import json
import logging
from typing import Any, Dict, List, Optional

from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.mejoralo")


def record_session(
    engine: CortexEngine,
    project: str,
    score_before: int,
    score_after: int,
    actions: Optional[List[str]] = None,
) -> int:
    """
    Record a MEJORAlo audit session in the CORTEX ledger.

    Returns:
        The fact ID of the persisted session record.
    """
    delta = score_after - score_before
    actions_str = "\n".join(f"  - {a}" for a in (actions or []))
    content = (
        f"MEJORAlo v7.3: Sesión completada.\n"
        f"Score: {score_before} → {score_after} (Δ{delta:+d})\n"
        f"Acciones:\n{actions_str}"
        if actions_str
        else f"MEJORAlo v7.3: Sesión completada. Score: {score_before} → {score_after} (Δ{delta:+d})"
    )

    fact_id = engine.store(
        project=project,
        content=content,
        fact_type="decision",
        tags=["mejoralo", "audit", "v7.3"],
        confidence="verified",
        source="cortex-mejoralo",
        meta={
            "score_before": score_before,
            "score_after": score_after,
            "delta": delta,
            "actions": actions or [],
            "version": "7.3",
        },
    )
    logger.info("Recorded MEJORAlo session #%d for project %s (Δ%+d)", fact_id, project, delta)
    return fact_id


def get_history(engine: CortexEngine, project: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve past MEJORAlo sessions from the ledger."""
    conn = engine._get_conn()
    rows = conn.execute(
        "SELECT id, content, created_at, meta "
        "FROM facts "
        "WHERE project = ? AND fact_type = 'decision' "
        "AND tags LIKE '%mejoralo%' AND valid_until IS NULL "
        "ORDER BY created_at DESC LIMIT ?",
        (project, limit),
    ).fetchall()

    results = []
    for row in rows:
        meta = {}
        try:
            meta = json.loads(row[3]) if row[3] else {}
        except (json.JSONDecodeError, TypeError):
            pass
        results.append(
            {
                "id": row[0],
                "content": row[1],
                "created_at": row[2],
                "score_before": meta.get("score_before"),
                "score_after": meta.get("score_after"),
                "delta": meta.get("delta"),
                "actions": meta.get("actions", []),
            }
        )
    return results

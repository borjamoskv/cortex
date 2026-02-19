"""
Staleness pruning strategy for compaction.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from cortex.engine import CortexEngine
    from cortex.compactor import CompactionResult

logger = logging.getLogger("cortex.compaction.staleness")
_LOG_FMT = "Compactor [%s] %s"


def execute_staleness_prune(
    engine: "CortexEngine",
    project: str,
    result: "CompactionResult",
    dry_run: bool,
    max_age_days: int,
    min_consensus: float,
) -> None:
    """Execute the STALENESS_PRUNE strategy."""
    stale_ids = find_stale_facts(engine, project, max_age_days, min_consensus)
    if not stale_ids:
        return

    result.strategies_applied.append("staleness_prune")
    if not dry_run:
        for fid in stale_ids:
            engine.deprecate_sync(fid, "compacted:stale")
            result.deprecated_ids.append(fid)

    detail = f"staleness_prune: {len(stale_ids)} stale facts"
    result.details.append(detail)
    logger.info(_LOG_FMT, project, detail)


def find_stale_facts(
    engine: "CortexEngine",
    project: str,
    max_age_days: int = 90,
    min_consensus: float = 0.5,
) -> List[int]:
    """Find facts older than max_age_days with consensus below min_consensus."""
    conn = engine._get_sync_conn()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()

    rows = conn.execute(
        "SELECT id FROM facts "
        "WHERE project = ? AND valid_until IS NULL "
        "AND created_at < ? AND consensus_score < ? "
        "ORDER BY created_at ASC",
        (project, cutoff, min_consensus),
    ).fetchall()

    return [r[0] for r in rows]

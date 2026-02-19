"""
Error merging strategy for compaction.
"""
import json
import logging
from collections import defaultdict
from typing import TYPE_CHECKING
from cortex.compaction.utils import content_hash, merge_error_contents

if TYPE_CHECKING:
    from cortex.engine import CortexEngine
    from cortex.compactor import CompactionResult

logger = logging.getLogger("cortex.compaction.merge_errors")
_LOG_FMT = "Compactor [%s] %s"


def execute_merge_errors(
    engine: "CortexEngine",
    project: str,
    result: "CompactionResult",
    dry_run: bool,
) -> None:
    """Execute the MERGE_ERRORS strategy."""
    conn = engine._get_sync_conn()
    error_rows = conn.execute(
        "SELECT id, content, tags, confidence, source "
        "FROM facts WHERE project = ? AND fact_type = 'error' "
        "AND valid_until IS NULL ORDER BY created_at ASC",
        (project,),
    ).fetchall()

    if len(error_rows) <= 1:
        return

    # Group by content hash
    hash_groups: dict[str, list[tuple]] = defaultdict(list)
    for row in error_rows:
        hash_groups[content_hash(row[1])].append(row)

    merged_count = 0
    for group in hash_groups.values():
        if len(group) <= 1:
            continue
        if not dry_run:
            _merge_error_group(engine, project, group, result)
        merged_count += len(group)

    if merged_count > 0:
        result.strategies_applied.append("merge_errors")
        unique_groups = sum(1 for g in hash_groups.values() if len(g) > 1)
        detail = f"merge_errors: consolidated {merged_count} → {unique_groups} error facts"
        result.details.append(detail)
        logger.info(_LOG_FMT, project, detail)


def _merge_error_group(
    engine: "CortexEngine",
    project: str,
    group: list[tuple],
    result: "CompactionResult",
) -> None:
    """Merge a single group of identical error facts."""
    canonical = group[0]
    contents = [r[1] for r in group]
    merged_content = merge_error_contents(contents)

    try:
        tags = json.loads(canonical[2]) if canonical[2] else None
    except (json.JSONDecodeError, TypeError):
        tags = None

    new_id = engine.store_sync(
        project=project,
        content=merged_content,
        fact_type="error",
        tags=tags,
        confidence=canonical[3] or "stated",
        source="compactor:merge_errors",
    )
    result.new_fact_ids.append(new_id)

    for row in group:
        engine.deprecate_sync(row[0], f"compacted:merge_errors→#{new_id}")
        result.deprecated_ids.append(row[0])

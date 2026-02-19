"""
Deduplication strategy for compaction.
"""
import logging
from collections import defaultdict
from typing import TYPE_CHECKING
from cortex.compaction.utils import content_hash, similarity

if TYPE_CHECKING:
    from cortex.engine import CortexEngine
    from cortex.compactor import CompactionResult

logger = logging.getLogger("cortex.compaction.dedup")
_LOG_FMT = "Compactor [%s] %s"


def execute_dedup(
    engine: "CortexEngine",
    project: str,
    result: "CompactionResult",
    dry_run: bool,
    threshold: float,
) -> None:
    """Execute the DEDUP strategy."""
    dup_groups = find_duplicates(engine, project, threshold)
    if not dup_groups:
        return

    result.strategies_applied.append("dedup")
    conn = engine._get_sync_conn()

    for group in dup_groups:
        canonical_id = group[0]
        if not dry_run:
            _merge_duplicate_group(engine, conn, canonical_id, group)
            result.deprecated_ids.extend(group[1:])

    total_removed = sum(len(g) - 1 for g in dup_groups)
    detail = f"dedup: {len(dup_groups)} groups, {total_removed} duplicates"
    result.details.append(detail)
    logger.info(_LOG_FMT, project, detail)


def find_duplicates(
    engine: "CortexEngine",
    project: str,
    similarity_threshold: float = 0.85,
) -> list[list[int]]:
    """Find groups of duplicate/near-duplicate facts.
    
    Returns list of groups where each group is list of fact IDs.
    First ID in each group is canonical (oldest).
    """
    conn = engine._get_sync_conn()
    rows = conn.execute(
        "SELECT id, content, fact_type, created_at "
        "FROM facts WHERE project = ? AND valid_until IS NULL "
        "ORDER BY created_at ASC",
        (project,),
    ).fetchall()

    if not rows:
        return []

    exact_groups, seen = _find_exact_duplicates(rows)
    near_groups = _find_near_duplicates(rows, seen, similarity_threshold)
    return exact_groups + near_groups


def _find_exact_duplicates(rows: list[tuple]) -> tuple[list[list[int]], set[int]]:
    """Phase 1: Group rows by content hash for exact duplicate detection."""
    hash_groups: dict[str, list[tuple]] = defaultdict(list)
    for row in rows:
        h = content_hash(row[1])
        hash_groups[h].append(row)

    groups: list[list[int]] = []
    seen: set[int] = set()
    for group in hash_groups.values():
        if len(group) > 1:
            ids = [r[0] for r in group]
            groups.append(ids)
            seen.update(ids)
    return groups, seen


def _find_near_duplicates(
    rows: list[tuple],
    seen_ids: set[int],
    threshold: float,
) -> list[list[int]]:
    """Phase 2: Levenshtein-based near-duplicate detection on remaining rows."""
    remaining = [r for r in rows if r[0] not in seen_ids]
    groups: list[list[int]] = []
    local_seen: set[int] = set()

    for i, row_i in enumerate(remaining):
        if row_i[0] in local_seen:
            continue
        group = [row_i[0]]
        for row_j in remaining[i + 1:]:
            if row_j[0] in local_seen:
                continue
            if row_i[2] != row_j[2]:  # same fact_type only
                continue
            if similarity(row_i[1], row_j[1]) >= threshold:
                group.append(row_j[0])
                local_seen.add(row_j[0])
        if len(group) > 1:
            local_seen.add(row_i[0])
            groups.append(group)

    return groups


def _merge_duplicate_group(
    engine: "CortexEngine",
    conn,
    canonical_id: int,
    group: list[int],
) -> None:
    """Merge a single duplicate group: deprecate duplicates, update canonical."""
    row = conn.execute(
        "SELECT content, fact_type FROM facts WHERE id = ?",
        (canonical_id,),
    ).fetchone()
    if not row:
        return

    # Collect all contents for merge
    all_contents = []
    from cortex.compaction.utils import merge_error_contents
    
    for fid in group:
        r = conn.execute("SELECT content FROM facts WHERE id = ?", (fid,)).fetchone()
        if r:
            all_contents.append(r[0])

    # Deprecate duplicates (not canonical)
    for dup_id in group[1:]:
        engine.deprecate_sync(dup_id, f"compacted:dedup→#{canonical_id}")

    # Update canonical if content changed after merge (only for errors usually)
    if row[1] == "error" and len(all_contents) > 1:
        merged = merge_error_contents(all_contents)
        if merged != row[0]:
            conn.execute(
                "UPDATE facts SET content = ?, updated_at = datetime('now') WHERE id = ?",
                (merged, canonical_id),
            )
            conn.commit()

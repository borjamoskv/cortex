"""
CORTEX v4.1 — Auto-Compaction Engine.

Fights context rot by deduplicating, consolidating, and pruning stale facts.
The compactor completes the memory lifecycle trinity:
  - pruner.py  → embedding lifecycle
  - compression.py → storage optimization
  - compactor.py → content-level compaction (this module)

Strategies:
  - DEDUP: SHA-256 exact + Levenshtein near-duplicate detection
  - MERGE_ERRORS: Consolidate repeated error facts into one
  - STALENESS_PRUNE: Deprecate old, low-consensus facts

Design: Zero data loss — originals are deprecated, never deleted.
Ledger hash-chain remains intact. time_travel still works.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.compactor")


_LOG_FMT = "Compactor [%s] %s"


# ─── Strategy Enum ───────────────────────────────────────────────────


class CompactionStrategy(str, Enum):
    """Available compaction strategies."""

    DEDUP = "dedup"
    MERGE_ERRORS = "merge_errors"
    STALENESS_PRUNE = "staleness_prune"

    @classmethod
    def all(cls) -> list[CompactionStrategy]:
        return list(cls)


# ─── Result Dataclass ────────────────────────────────────────────────


@dataclass
class CompactionResult:
    """Outcome of a compaction run."""

    project: str
    strategies_applied: list[str] = field(default_factory=list)
    original_count: int = 0
    compacted_count: int = 0
    deprecated_ids: list[int] = field(default_factory=list)
    new_fact_ids: list[int] = field(default_factory=list)
    dry_run: bool = False
    details: list[str] = field(default_factory=list)

    @property
    def reduction(self) -> int:
        return self.original_count - self.compacted_count

    def to_dict(self) -> dict:
        return {
            "project": self.project,
            "strategies_applied": self.strategies_applied,
            "original_count": self.original_count,
            "compacted_count": self.compacted_count,
            "reduction": self.reduction,
            "deprecated_ids": self.deprecated_ids,
            "new_fact_ids": self.new_fact_ids,
            "dry_run": self.dry_run,
            "details": self.details,
        }


# ─── Helpers ─────────────────────────────────────────────────────────


def _normalize_content(text: str) -> str:
    """Normalize text for comparison: lowercase, strip, collapse whitespace."""
    return " ".join(text.lower().strip().split())


def _content_hash(text: str) -> str:
    """SHA-256 hash of normalized content."""
    return hashlib.sha256(_normalize_content(text).encode("utf-8")).hexdigest()


def _similarity(a: str, b: str) -> float:
    """Levenshtein-based similarity ratio (0.0–1.0)."""
    return SequenceMatcher(None, _normalize_content(a), _normalize_content(b)).ratio()


def _merge_error_contents(contents: list[str]) -> str:
    """Merge multiple error messages into one consolidated fact."""
    unique_msgs = list(dict.fromkeys(contents))
    if len(unique_msgs) == 1:
        return f"{unique_msgs[0]} (occurred {len(contents)}×)"
    combined = " | ".join(msg[:200] for msg in unique_msgs[:5])
    return f"[Consolidated {len(contents)} errors] {combined}"


# ─── Duplicate Detection ────────────────────────────────────────────


def _find_exact_duplicates(rows: list[tuple]) -> tuple[list[list[int]], set[int]]:
    """Phase 1: Group rows by content hash for exact duplicate detection."""
    hash_groups: dict[str, list[tuple]] = defaultdict(list)
    for row in rows:
        h = _content_hash(row[1])
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
            if _similarity(row_i[1], row_j[1]) >= threshold:
                group.append(row_j[0])
                local_seen.add(row_j[0])
        if len(group) > 1:
            local_seen.add(row_i[0])
            groups.append(group)

    return groups


def find_duplicates(
    engine: CortexEngine,
    project: str,
    similarity_threshold: float = 0.85,
) -> list[list[int]]:
    """Find groups of duplicate/near-duplicate facts.

    Returns list of groups where each group is a list of fact IDs.
    First ID in each group is the canonical (oldest) fact.
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


def find_stale_facts(
    engine: CortexEngine,
    project: str,
    max_age_days: int = 90,
    min_consensus: float = 0.5,
) -> list[int]:
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


# ─── Strategy Executors ──────────────────────────────────────────────


def _execute_dedup(
    engine: CortexEngine,
    project: str,
    result: CompactionResult,
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


def _merge_duplicate_group(
    engine: CortexEngine,
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
    for fid in group:
        r = conn.execute("SELECT content FROM facts WHERE id = ?", (fid,)).fetchone()
        if r:
            all_contents.append(r[0])

    # Deprecate duplicates (not canonical)
    for dup_id in group[1:]:
        engine.deprecate_sync(dup_id, f"compacted:dedup→#{canonical_id}")

    # Update canonical if content changed after merge
    if row[1] == "error" and len(all_contents) > 1:
        merged = _merge_error_contents(all_contents)
        if merged != row[0]:
            conn.execute(
                "UPDATE facts SET content = ?, updated_at = datetime('now') WHERE id = ?",
                (merged, canonical_id),
            )
            conn.commit()


def _execute_merge_errors(
    engine: CortexEngine,
    project: str,
    result: CompactionResult,
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
        hash_groups[_content_hash(row[1])].append(row)

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
    engine: CortexEngine,
    project: str,
    group: list[tuple],
    result: CompactionResult,
) -> None:
    """Merge a single group of identical error facts."""
    canonical = group[0]
    contents = [r[1] for r in group]
    merged_content = _merge_error_contents(contents)

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


def _execute_staleness_prune(
    engine: CortexEngine,
    project: str,
    result: CompactionResult,
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


# ─── Main Entry Point ───────────────────────────────────────────────


def compact(
    engine: CortexEngine,
    project: str,
    strategies: list[CompactionStrategy] | None = None,
    dry_run: bool = False,
    similarity_threshold: float = 0.85,
    max_age_days: int = 90,
    min_consensus: float = 0.5,
) -> CompactionResult:
    """Run compaction on a project. Main entry point.

    Applies selected strategies in order, deprecating originals
    and creating consolidated facts. Zero data loss.
    """
    if strategies is None:
        strategies = CompactionStrategy.all()

    conn = engine._get_sync_conn()
    count_before = conn.execute(
        "SELECT COUNT(*) FROM facts WHERE project = ? AND valid_until IS NULL",
        (project,),
    ).fetchone()[0]

    result = CompactionResult(
        project=project, original_count=count_before, dry_run=dry_run
    )

    # Dispatch strategies
    if CompactionStrategy.DEDUP in strategies:
        _execute_dedup(engine, project, result, dry_run, similarity_threshold)

    if CompactionStrategy.MERGE_ERRORS in strategies:
        _execute_merge_errors(engine, project, result, dry_run)

    if CompactionStrategy.STALENESS_PRUNE in strategies:
        _execute_staleness_prune(
            engine, project, result, dry_run, max_age_days, min_consensus
        )

    # Final count
    count_after = conn.execute(
        "SELECT COUNT(*) FROM facts WHERE project = ? AND valid_until IS NULL",
        (project,),
    ).fetchone()[0]
    result.compacted_count = count_after

    # Log compaction
    if not dry_run and result.deprecated_ids:
        _log_compaction(
            conn,
            project=project,
            strategies=list(result.strategies_applied),
            original_ids=result.deprecated_ids,
            new_fact_ids=result.new_fact_ids,
            facts_before=count_before,
            facts_after=count_after,
        )

    logger.info(
        "Compaction [%s] complete: %d → %d facts (-%d)%s",
        project,
        count_before,
        count_after,
        result.reduction,
        " (dry-run)" if dry_run else "",
    )
    return result


# ─── Session Compaction ──────────────────────────────────────────────


_TYPE_ORDER = ["axiom", "decision", "rule", "error", "knowledge", "ghost", "intent", "schema"]


def compact_session(
    engine: CortexEngine,
    project: str,
    max_facts: int = 50,
) -> str:
    """Prepare compressed context string for LLM re-injection.

    Selects most relevant active facts, groups by type,
    produces dense markdown summary.
    """
    conn = engine._get_sync_conn()
    rows = conn.execute(
        "SELECT id, content, fact_type, tags, consensus_score, created_at "
        "FROM facts WHERE project = ? AND valid_until IS NULL "
        "ORDER BY "
        "  CASE fact_type "
        "    WHEN 'axiom' THEN 0 WHEN 'decision' THEN 1 "
        "    WHEN 'rule' THEN 2 WHEN 'error' THEN 3 "
        "    WHEN 'knowledge' THEN 4 WHEN 'ghost' THEN 5 "
        "    ELSE 6 END, "
        "  consensus_score DESC, created_at DESC "
        "LIMIT ?",
        (project, max_facts),
    ).fetchall()

    if not rows:
        return f"# {project}\n\nNo active facts.\n"

    by_type: dict[str, list[tuple]] = defaultdict(list)
    for row in rows:
        by_type[row[2]].append(row)

    return _format_session_context(project, by_type)


def _format_session_context(project: str, by_type: dict[str, list[tuple]]) -> str:
    """Format grouped facts into markdown context."""
    lines = [f"# {project}", ""]

    for ft in _TYPE_ORDER:
        if ft in by_type:
            _append_type_section(lines, ft, by_type[ft])

    # Remaining types not in the predefined order
    for ft, facts in by_type.items():
        if ft not in _TYPE_ORDER:
            _append_type_section(lines, ft, facts)

    return "\n".join(lines)


def _append_type_section(lines: list[str], fact_type: str, facts: list[tuple]) -> None:
    """Append a fact type section to the output lines."""
    lines.append(f"## {fact_type.capitalize()} ({len(facts)})")
    lines.append("")
    for row in facts:
        lines.append(f"- {row[1][:200]}")
    lines.append("")


# ─── Stats ───────────────────────────────────────────────────────────


def get_compaction_stats(
    engine: CortexEngine,
    project: str | None = None,
) -> dict:
    """Get compaction history and statistics."""
    conn = engine._get_sync_conn()

    table_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='compaction_log'"
    ).fetchone()

    if not table_exists:
        return {"total_compactions": 0, "total_deprecated": 0, "history": []}

    query = "SELECT * FROM compaction_log"
    params: list = []
    if project:
        query += " WHERE project = ?"
        params.append(project)
    query += " ORDER BY timestamp DESC LIMIT 20"

    rows = conn.execute(query, params).fetchall()
    history = []
    total_deprecated = 0

    for row in rows:
        original_ids = json.loads(row[3]) if row[3] else []
        total_deprecated += len(original_ids)
        history.append({
            "id": row[0],
            "project": row[1],
            "strategy": row[2],
            "deprecated_count": len(original_ids),
            "new_fact_id": row[4],
            "facts_before": row[5],
            "facts_after": row[6],
            "timestamp": row[7],
        })

    return {
        "total_compactions": len(rows),
        "total_deprecated": total_deprecated,
        "history": history,
    }


# ─── Internal ────────────────────────────────────────────────────────


def _log_compaction(
    conn,
    project: str,
    strategies: list[str],
    original_ids: list[int],
    new_fact_ids: list[int],
    facts_before: int,
    facts_after: int,
) -> None:
    """Log a compaction event to the compaction_log table."""
    try:
        conn.execute(
            "INSERT INTO compaction_log "
            "(project, strategy, original_ids, new_fact_id, facts_before, facts_after) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                project,
                ",".join(strategies),
                json.dumps(original_ids),
                new_fact_ids[0] if new_fact_ids else None,
                facts_before,
                facts_after,
            ),
        )
        conn.commit()
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.warning("Failed to log compaction: %s", e)

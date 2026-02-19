"""
Context formatting utilities for Cortex sessions.
"""
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

_TYPE_ORDER = ["axiom", "decision", "rule", "error", "knowledge", "ghost", "intent", "schema"]


def compact_session(
    engine: "CortexEngine",
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

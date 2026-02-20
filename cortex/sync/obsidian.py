"""CORTEX v4 — Obsidian Vault Export.

Exports the entire CORTEX memory as an interconnected Obsidian vault.
Each fact becomes a Markdown note with YAML frontmatter and [[wikilinks]].

Usage:
    cortex obsidian --out ~/CORTEX-Vault
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from cortex.temporal import now_iso

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.sync.obsidian")

# ─── Type → Folder mapping ─────────────────────────────────────────
TYPE_FOLDERS: dict[str, str] = {
    "decision": "decisions",
    "error": "errors",
    "ghost": "ghosts",
    "knowledge": "knowledge",
    "bridge": "bridges",
    "pattern": "patterns",
    "reflection": "reflections",
}

# ─── Emoji for types ───────────────────────────────────────────────
TYPE_EMOJI: dict[str, str] = {
    "decision": "⚡",
    "error": "🔴",
    "ghost": "👻",
    "knowledge": "📘",
    "bridge": "🌉",
    "pattern": "🧩",
    "reflection": "🪞",
}


def _slugify(text: str) -> str:
    """Convert text to a safe filename slug."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug[:80].strip("-")


def _render_frontmatter(data: dict) -> str:
    """Render YAML frontmatter block."""
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            if value:
                items = ", ".join(str(v) for v in value)
                lines.append(f"{key}: [{items}]")
            else:
                lines.append(f"{key}: []")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        elif value is None:
            lines.append(f"{key}: null")
        else:
            # Escape quotes in strings
            safe = str(value).replace('"', '\\"')
            lines.append(f'{key}: "{safe}"')
    lines.append("---")
    return "\n".join(lines)


def _render_fact_note(fact: dict) -> str:
    """Render a single fact as an Obsidian Markdown note."""
    fact_type = fact["type"]
    emoji = TYPE_EMOJI.get(fact_type, "📝")

    frontmatter = _render_frontmatter({
        "id": fact["id"],
        "type": fact_type,
        "project": fact["project"],
        "confidence": fact["confidence"],
        "tags": fact["tags"],
        "consensus_score": fact.get("consensus_score", 1.0),
        "created_at": fact["created_at"],
        "updated_at": fact.get("updated_at"),
        "active": fact.get("active", True),
    })

    # Build note body
    lines = [
        frontmatter,
        "",
        f"# {emoji} {fact_type.capitalize()} #{fact['id']}",
        "",
        fact["content"],
        "",
        "---",
        "",
        f"**Project:** [[{fact['project']}]]",
        f"**Type:** `{fact_type}`",
        f"**Confidence:** `{fact['confidence']}`",
    ]

    if fact["tags"]:
        tag_links = " · ".join(f"[[{tag}]]" for tag in fact["tags"])
        lines.append(f"**Tags:** {tag_links}")

    lines.extend([
        f"**Created:** {fact['created_at'][:10]}",
        "",
    ])

    return "\n".join(lines)


def _render_project_moc(project: str, facts: list[dict]) -> str:
    """Render a project Map of Content note."""
    # Group by type
    by_type: dict[str, list[dict]] = {}
    for f in facts:
        by_type.setdefault(f["type"], []).append(f)

    lines = [
        _render_frontmatter({
            "type": "moc",
            "project": project,
            "total_facts": len(facts),
        }),
        "",
        f"# 📂 {project}",
        "",
        f"> {len(facts)} active facts",
        "",
    ]

    for ftype, type_facts in sorted(by_type.items()):
        emoji = TYPE_EMOJI.get(ftype, "📝")
        lines.append(f"## {emoji} {ftype.capitalize()} ({len(type_facts)})")
        lines.append("")
        for f in type_facts:
            preview = f["content"][:100]
            if len(f["content"]) > 100:
                preview += "..."
            folder = TYPE_FOLDERS.get(ftype, ftype)
            filename = f"{ftype}-{f['id']}"
            lines.append(f"- [[{folder}/{filename}|#{f['id']}]] — {preview}")
        lines.append("")

    return "\n".join(lines)


def _render_tag_note(tag: str, facts: list[dict]) -> str:
    """Render a tag index note."""
    lines = [
        _render_frontmatter({"type": "tag-index", "tag": tag, "count": len(facts)}),
        "",
        f"# 🏷️ {tag}",
        "",
        f"> {len(facts)} facts tagged with `{tag}`",
        "",
    ]

    for f in facts:
        preview = f["content"][:100]
        if len(f["content"]) > 100:
            preview += "..."
        folder = TYPE_FOLDERS.get(f["type"], f["type"])
        filename = f"{f['type']}-{f['id']}"
        lines.append(f"- [[{folder}/{filename}|#{f['id']}]] ({f['project']}) — {preview}")

    lines.append("")
    return "\n".join(lines)


def _render_dashboard(
    projects: dict[str, list[dict]],
    total_facts: int,
    type_counts: dict[str, int],
) -> str:
    """Render the main CORTEX Dashboard MOC."""
    lines = [
        _render_frontmatter({
            "type": "dashboard",
            "generated": now_iso(),
            "total_facts": total_facts,
            "total_projects": len(projects),
        }),
        "",
        "# 🧠 CORTEX Dashboard",
        "",
        f"> {total_facts} facts across {len(projects)} projects",
        f"> Generated: {now_iso()[:10]}",
        "",
        "## 📊 Overview",
        "",
    ]

    # Type distribution
    lines.append("| Type | Count |")
    lines.append("|:---|---:|")
    for ftype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        emoji = TYPE_EMOJI.get(ftype, "📝")
        lines.append(f"| {emoji} {ftype} | {count} |")
    lines.append("")

    # Project index
    lines.append("## 📂 Projects")
    lines.append("")
    for project, facts in sorted(projects.items()):
        lines.append(f"- [[projects/{project}|{project}]] — {len(facts)} facts")
    lines.append("")

    return "\n".join(lines)


def _parse_fact_rows(rows: list) -> list[dict]:
    """Parse raw DB rows into fact dicts."""
    facts: list[dict] = []
    for row in rows:
        facts.append({
            "id": row[0],
            "project": row[1],
            "content": row[2],
            "type": row[3],
            "tags": json.loads(row[4]) if row[4] else [],
            "confidence": row[5],
            "consensus_score": row[6] if row[6] is not None else 1.0,
            "created_at": row[7] or "",
            "updated_at": row[8] or "",
            "active": row[9] is None,
        })
    return facts


def _group_facts(facts: list[dict]) -> tuple[dict, dict, dict]:
    """Group facts by project, tag, and count types."""
    by_project: dict[str, list[dict]] = {}
    by_tag: dict[str, list[dict]] = {}
    type_counts: dict[str, int] = {}

    for f in facts:
        by_project.setdefault(f["project"], []).append(f)
        type_counts[f["type"]] = type_counts.get(f["type"], 0) + 1
        for tag in f["tags"]:
            by_tag.setdefault(tag, []).append(f)

    return by_project, by_tag, type_counts


def _write_vault(
    vault_path: Path,
    facts: list[dict],
    by_project: dict[str, list[dict]],
    by_tag: dict[str, list[dict]],
    type_counts: dict[str, int],
) -> int:
    """Write all vault files and return notes_created count."""
    notes_created = 0

    # Create type folders
    all_folders = set(TYPE_FOLDERS.values()) | {"projects", "tags"}
    for folder in all_folders:
        (vault_path / folder).mkdir(parents=True, exist_ok=True)

    # 1. Individual fact notes
    for f in facts:
        folder = TYPE_FOLDERS.get(f["type"], f["type"])
        folder_path = vault_path / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        filename = f"{f['type']}-{f['id']}.md"
        (folder_path / filename).write_text(_render_fact_note(f), encoding="utf-8")
        notes_created += 1

    # 2. Project MOC notes
    for project, proj_facts in by_project.items():
        content = _render_project_moc(project, proj_facts)
        (vault_path / "projects" / f"{project}.md").write_text(content, encoding="utf-8")
        notes_created += 1

    # 3. Tag index notes
    for tag, tag_facts in by_tag.items():
        safe_tag = _slugify(tag) or "untagged"
        content = _render_tag_note(tag, tag_facts)
        (vault_path / "tags" / f"{safe_tag}.md").write_text(content, encoding="utf-8")
        notes_created += 1

    # 4. Dashboard MOC
    dashboard = _render_dashboard(by_project, len(facts), type_counts)
    (vault_path / "🧠 CORTEX Dashboard.md").write_text(dashboard, encoding="utf-8")
    notes_created += 1

    return notes_created


async def export_obsidian(
    engine: CortexEngine,
    vault_path: Path | None = None,
) -> dict:
    """Export CORTEX memory as an interconnected Obsidian vault.

    Args:
        engine: CortexEngine instance.
        vault_path: Output directory for the vault. Defaults to ~/.cortex/obsidian-vault/

    Returns:
        Dict with export stats: notes_created, projects, types, tags.
    """
    from cortex.sync.common import CORTEX_DIR

    if vault_path is None:
        vault_path = CORTEX_DIR / "obsidian-vault"

    vault_path = Path(vault_path)

    # ─── Fetch all active facts ─────────────────────────────────────
    conn = await engine.get_conn()
    async with conn.execute(
        "SELECT id, project, content, fact_type, tags, confidence, "
        "consensus_score, created_at, updated_at, valid_until "
        "FROM facts WHERE valid_until IS NULL "
        "ORDER BY project, fact_type, id"
    ) as cursor:
        rows = await cursor.fetchall()

    facts = _parse_fact_rows(rows)
    by_project, by_tag, type_counts = _group_facts(facts)
    notes_created = _write_vault(vault_path, facts, by_project, by_tag, type_counts)

    stats = {
        "vault_path": str(vault_path),
        "notes_created": notes_created,
        "total_facts": len(facts),
        "projects": list(by_project.keys()),
        "types": type_counts,
        "tags": list(by_tag.keys()),
    }

    logger.info(
        "Obsidian vault exported to %s (%d notes, %d facts)",
        vault_path,
        notes_created,
        len(facts),
    )

    return stats


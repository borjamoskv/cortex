"""
CORTEX v4.0 — Export Module.

Supports JSON, CSV, and JSONL export formats for project facts.
"""

from __future__ import annotations

import csv
import io
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.engine import Fact


def export_facts(facts: list[Fact], fmt: str = "json") -> str:
    """Export facts to the specified format.

    Args:
        facts: List of Fact objects.
        fmt: Format — 'json', 'csv', or 'jsonl'.

    Returns:
        Formatted string.

    Raises:
        ValueError: If format is unsupported.
    """
    fmt = fmt.lower().strip()
    if fmt == "json":
        return _export_json(facts)
    elif fmt == "csv":
        return _export_csv(facts)
    elif fmt == "jsonl":
        return _export_jsonl(facts)
    else:
        raise ValueError(f"Unsupported export format: '{fmt}'. Use: json, csv, jsonl")


def _export_json(facts: list[Fact]) -> str:
    """Export as pretty-printed JSON array."""
    return json.dumps([f.to_dict() for f in facts], indent=2, ensure_ascii=False)


def _export_csv(facts: list[Fact]) -> str:
    """Export as CSV with headers."""
    if not facts:
        return ""

    output = io.StringIO()
    fieldnames = [
        "id",
        "project",
        "content",
        "fact_type",
        "tags",
        "confidence",
        "valid_from",
        "valid_until",
        "source",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for f in facts:
        d = f.to_dict()
        # Flatten tags list to semicolon-separated string
        d["tags"] = ";".join(d.get("tags", []))
        writer.writerow({k: d.get(k, "") for k in fieldnames})

    return output.getvalue()


def _export_jsonl(facts: list[Fact]) -> str:
    """Export as JSON Lines (one JSON object per line)."""
    lines = [json.dumps(f.to_dict(), ensure_ascii=False) for f in facts]
    return "\n".join(lines)

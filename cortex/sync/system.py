"""Sync System: Syncs system.json (knowledge/decisions) to CORTEX DB."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from cortex.sync.common import SyncResult, calculate_fact_diff, get_existing_contents

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.sync")


def sync_system(engine: CortexEngine, path: Path, result: SyncResult) -> None:
    """Sincroniza system.json — conocimiento global y decisiones."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        result.errors.append(f"Error leyendo system.json: {e}")
        return

    # Obtener contenidos existentes para dedup
    existing = get_existing_contents(engine, "__system__")

    # knowledge_global
    kb_candidates = data.get("knowledge_global", [])
    new_kb = calculate_fact_diff(existing, kb_candidates, lambda x: x.get("content", str(x)))
    for content, kb in new_kb:
        try:
            engine.store(
                project="__system__",
                content=content,
                fact_type="knowledge",
                tags=["sistema", kb.get("topic", "general")],
                confidence=kb.get("confidence", "stated"),
                source="sync-agent-memory",
                valid_from=kb.get("added") or kb.get("date"),
                meta=kb,
            )
            result.facts_synced += 1
            existing.add(content)
        except Exception as e:
            result.errors.append(f"Error system knowledge: {e}")

    # decisions_global
    dec_candidates = data.get("decisions_global", [])
    new_dec = calculate_fact_diff(
        existing,
        dec_candidates,
        lambda x: f"DECISION: {x.get('decision', str(x))} | RAZON: {x.get('reason', '')}",
    )
    for content, dec in new_dec:
        try:
            engine.store(
                project="__system__",
                content=content,
                fact_type="decision",
                tags=["sistema", "decision-global", dec.get("topic", "")],
                confidence="verified",
                source="sync-agent-memory",
                valid_from=dec.get("date"),
                meta=dec,
            )
            result.facts_synced += 1
            existing.add(content)
        except Exception as e:
            result.errors.append(f"Error system decision: {e}")

    # Ecosistema
    eco = data.get("ecosystem", {})
    if eco:
        eco_content = (
            f"Ecosistema: {eco.get('total_projects', '?')} proyectos | "
            f"Foco: {', '.join(eco.get('active_focus', []))} | "
            f"Diagnóstico: {eco.get('diagnosis', 'sin datos')}"
        )
        if eco_content not in existing:
            try:
                engine.store(
                    project="__system__",
                    content=eco_content,
                    fact_type="knowledge",
                    tags=["sistema", "ecosistema"],
                    confidence="verified",
                    source="sync-agent-memory",
                    meta=eco,
                )
                result.facts_synced += 1
            except Exception as e:
                result.errors.append(f"Error ecosystem sync: {e}")

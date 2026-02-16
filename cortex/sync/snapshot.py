"""Sync Engine: Snapshot Export."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from cortex.sync.common import CORTEX_DIR
from cortex.temporal import now_iso

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.sync")


async def export_snapshot(engine: CortexEngine, out_path: Path | None = None) -> Path:
    """Exporta un snapshot legible de toda la memoria activa de CORTEX.

    Genera un archivo markdown que el agente IA puede leer al inicio
    de cada conversación para tener contexto completo.

    Args:
        engine: Instancia de CortexEngine.
        out_path: Ruta de salida. Por defecto ~/.cortex/context-snapshot.md

    Returns:
        Path del archivo generado.
    """
    if out_path is None:
        out_path = CORTEX_DIR / "context-snapshot.md"

    conn = await engine.get_conn()
    async with conn.execute(
        "SELECT project, content, fact_type, tags, confidence "
        "FROM facts WHERE valid_until IS NULL "
        "ORDER BY project, fact_type, id"
    ) as cursor:
        rows = await cursor.fetchall()

    # Agrupar por proyecto
    by_project: dict[str, list] = {}
    for row in rows:
        project = row[0]
        by_project.setdefault(project, []).append(
            {
                "content": row[1],
                "type": row[2],
                "tags": json.loads(row[3]) if row[3] else [],
                "confidence": row[4],
            }
        )

    lines = [
        "# 🧠 CORTEX — Snapshot de Memoria",
        "",
        f"> Generado automáticamente: {now_iso()}",
        f"> Total: {len(rows)} facts activos en {len(by_project)} proyectos",
        "",
    ]

    stats = await engine.stats()
    db_path = engine._db_path
    db_size_mb = db_path.stat().st_size / (1024 * 1024) if db_path.exists() else 0.0

    lines.extend(
        [
            "## Estado del Sistema",
            "",
            f"- **DB:** {db_path} ({db_size_mb:.2f} MB)",
            f"- **Facts activos:** {stats['active_facts']}",
            f"- **Proyectos:** {', '.join(stats['projects'])}",
            f"- **Tipos:** {', '.join(f'{t}: {c}' for t, c in stats['types'].items())}",
            "",
        ]
    )

    for project, facts in by_project.items():
        display_name = project.replace("__", "").upper() if project.startswith("__") else project
        lines.append(f"## {display_name}")
        lines.append("")

        # Agrupar por tipo dentro del proyecto
        by_type: dict[str, list] = {}
        for f in facts:
            by_type.setdefault(f["type"], []).append(f)

        for ftype, type_facts in by_type.items():
            lines.append(f"### {ftype.capitalize()} ({len(type_facts)})")
            lines.append("")
            for f in type_facts:
                # Contenido truncado para legibilidad
                content = f["content"][:200]
                if len(f["content"]) > 200:
                    content += "..."
                lines.append(f"- {content}")
            lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")

    logger.info("Snapshot exportado a %s (%d facts)", out_path, len(rows))
    return out_path

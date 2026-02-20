"""Sync Engine: Write (DB -> Memory/Artifacts)."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from typing import TYPE_CHECKING

from cortex.sync.common import (
    MEMORY_DIR,
    WritebackResult,
    atomic_write,
    db_content_hash,
    load_sync_state,
    save_sync_state,
)
from cortex.temporal import now_iso

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.sync")


def export_to_json(engine: CortexEngine) -> WritebackResult:
    """Write-back: CORTEX DB → ~/.agent/memory/ (DB es Source of Truth).

    Reconstruye los archivos JSON originales a partir del estado actual
    de la base de datos CORTEX. Usa detección de cambios por SHA-256
    y escritura atómica para prevenir corrupción.

    Archivos generados:
    - ghosts.json     ← facts tipo 'ghost'
    - system.json     ← facts tipo 'knowledge' + 'decision'
    - mistakes.jsonl  ← facts tipo 'error'
    - bridges.jsonl   ← facts tipo 'bridge'

    Returns:
        WritebackResult con estadísticas.
    """
    result = WritebackResult()
    state = load_sync_state()
    wb_hashes = state.get("writeback_hashes", {})

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. Ghosts → ghosts.json ──────────────────────────────────
    try:
        db_hash = db_content_hash(engine, "ghost")
        if db_hash != wb_hashes.get("ghost"):
            _writeback_ghosts(engine, result)
            wb_hashes["ghost"] = db_hash
        else:
            result.files_skipped += 1
    except (sqlite3.Error, json.JSONDecodeError, OSError) as e:
        result.errors.append(f"ghost: {e}")
        logger.exception("Write-back ghosts failed")

    # ── 2. System (knowledge + decisions) → system.json ──────────
    try:
        k_hash = db_content_hash(engine, "knowledge")
        d_hash = db_content_hash(engine, "decision")
        combined_hash = hashlib.sha256(f"{k_hash}:{d_hash}".encode()).hexdigest()
        if combined_hash != wb_hashes.get("system"):
            _writeback_system(engine, result)
            wb_hashes["system"] = combined_hash
        else:
            result.files_skipped += 1
    except (sqlite3.Error, json.JSONDecodeError, OSError) as e:
        result.errors.append(f"system: {e}")
        logger.exception("Write-back system failed")

    # ── 3. Mistakes → mistakes.jsonl ─────────────────────────────
    try:
        db_hash = db_content_hash(engine, "error")
        if db_hash != wb_hashes.get("error"):
            _writeback_mistakes(engine, result)
            wb_hashes["error"] = db_hash
        else:
            result.files_skipped += 1
    except (sqlite3.Error, json.JSONDecodeError, OSError) as e:
        result.errors.append(f"error: {e}")
        logger.exception("Write-back mistakes failed")

    # ── 4. Bridges → bridges.jsonl ───────────────────────────────
    try:
        db_hash = db_content_hash(engine, "bridge")
        if db_hash != wb_hashes.get("bridge"):
            _writeback_bridges(engine, result)
            wb_hashes["bridge"] = db_hash
        else:
            result.files_skipped += 1
    except (sqlite3.Error, json.JSONDecodeError, OSError) as e:
        result.errors.append(f"bridge: {e}")
        logger.exception("Write-back bridges failed")

    # Guardar hashes para la próxima ejecución
    state["writeback_hashes"] = wb_hashes
    state["last_writeback"] = now_iso()
    save_sync_state(state)

    if result.had_changes:
        logger.info(
            "Write-back completado: %d archivos actualizados, %d items exportados",
            result.files_written,
            result.items_exported,
        )
    else:
        logger.debug("Write-back: sin cambios en DB desde la última exportación")

    return result


def _writeback_ghosts(engine: CortexEngine, result: WritebackResult) -> None:
    """Reconstruye ghosts.json desde facts tipo 'ghost'."""
    conn = engine._get_sync_conn()
    rows = conn.execute(
        "SELECT project, meta FROM facts "
        "WHERE fact_type = 'ghost' AND valid_until IS NULL "
        "ORDER BY project"
    ).fetchall()

    ghosts = {}
    for row in rows:
        project = row[0]
        meta = json.loads(row[1]) if row[1] else {}
        ghosts[project] = meta

    content = json.dumps(ghosts, indent=2, ensure_ascii=False, sort_keys=True)
    atomic_write(MEMORY_DIR / "ghosts.json", content)

    result.files_written += 1
    result.items_exported += len(ghosts)
    logger.info("Write-back ghosts: %d proyectos", len(ghosts))


def _writeback_system(engine: CortexEngine, result: WritebackResult) -> None:
    """Reconstruye system.json desde facts tipo 'knowledge' y 'decision'."""
    conn = engine._get_sync_conn()

    # Leer system.json existente para preservar estructura
    system_path = MEMORY_DIR / "system.json"
    if system_path.exists():
        try:
            system_data = json.loads(system_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            system_data = {}
    else:
        system_data = {}

    # Knowledge global — reconstruir desde DB
    k_rows = conn.execute(
        "SELECT content, tags, confidence, valid_from, meta FROM facts "
        "WHERE project = '__system__' AND fact_type = 'knowledge' "
        "AND valid_until IS NULL ORDER BY id"
    ).fetchall()

    knowledge_list = []
    for row in k_rows:
        meta = json.loads(row[4]) if row[4] else {}
        knowledge_list.append(
            {
                "id": meta.get("id", f"K{len(knowledge_list) + 1:03d}"),
                "topic": meta.get("topic", "general"),
                "content": row[0],
                "added": row[3] or "",
                "confidence": row[2] or "stated",
            }
        )

    # Decisions global — reconstruir desde DB
    d_rows = conn.execute(
        "SELECT content, meta FROM facts "
        "WHERE project = '__system__' AND fact_type = 'decision' "
        "AND valid_until IS NULL ORDER BY id"
    ).fetchall()

    decisions_list = []
    for row in d_rows:
        meta = json.loads(row[1]) if row[1] else {}
        decisions_list.append(
            {
                "id": meta.get("id", f"D{len(decisions_list) + 1:03d}"),
                "decision": row[0],
                **{k: v for k, v in meta.items() if k != "id"},
            }
        )

    system_data["knowledge_global"] = knowledge_list
    system_data["decisions_global"] = decisions_list
    system_data.setdefault("meta", {})["last_updated"] = now_iso()

    content = json.dumps(system_data, indent=2, ensure_ascii=False)
    atomic_write(system_path, content)

    count = len(knowledge_list) + len(decisions_list)
    result.files_written += 1
    result.items_exported += count
    logger.info(
        "Write-back system: %d knowledge + %d decisions", len(knowledge_list), len(decisions_list)
    )


def _writeback_mistakes(engine: CortexEngine, result: WritebackResult) -> None:
    """Reconstruye mistakes.jsonl desde facts tipo 'error'."""
    conn = engine._get_sync_conn()
    rows = conn.execute(
        "SELECT project, content, tags, valid_from, meta FROM facts "
        "WHERE fact_type = 'error' AND valid_until IS NULL ORDER BY id"
    ).fetchall()

    lines = []
    for row in rows:
        meta = json.loads(row[4]) if row[4] else {}
        # Reconstruir el formato original de mistakes.jsonl
        entry = {
            "date": row[3] or meta.get("date", ""),
            "project": row[0],
            "error": meta.get("error", ""),
            "root_cause": meta.get("root_cause", ""),
            "fix": meta.get("fix", ""),
            "tags": json.loads(row[2]) if row[2] else [],
        }
        lines.append(json.dumps(entry, ensure_ascii=False))

    content = "\n".join(lines) + "\n" if lines else ""
    atomic_write(MEMORY_DIR / "mistakes.jsonl", content)

    result.files_written += 1
    result.items_exported += len(lines)
    logger.info("Write-back mistakes: %d errores", len(lines))


def _writeback_bridges(engine: CortexEngine, result: WritebackResult) -> None:
    """Reconstruye bridges.jsonl desde facts tipo 'bridge'."""
    conn = engine._get_sync_conn()
    rows = conn.execute(
        "SELECT content, tags, valid_from, meta FROM facts "
        "WHERE fact_type = 'bridge' AND valid_until IS NULL ORDER BY id"
    ).fetchall()

    lines = []
    for row in rows:
        meta = json.loads(row[3]) if row[3] else {}
        tags = json.loads(row[1]) if row[1] else []
        # Reconstruir formato original de bridges.jsonl
        entry = {
            "date": row[2] or meta.get("date", ""),
            "from": meta.get("from", tags[0] if len(tags) > 0 else ""),
            "to": meta.get("to", tags[1] if len(tags) > 1 else ""),
            "pattern": meta.get("pattern", tags[2] if len(tags) > 2 else ""),
            "note": meta.get("note", ""),
        }
        lines.append(json.dumps(entry, ensure_ascii=False))

    content = "\n".join(lines) + "\n" if lines else ""
    atomic_write(MEMORY_DIR / "bridges.jsonl", content)

    result.files_written += 1
    result.items_exported += len(lines)
    logger.info("Write-back bridges: %d bridges", len(lines))

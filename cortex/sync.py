"""
CORTEX v4.0 — Sincronización continua de memoria.

Lee los archivos JSON de ~/.agent/memory/ y sincroniza los cambios
en la base de datos CORTEX. A diferencia de migrate.py (importación
one-shot), sync es incremental e idempotente: detecta qué ha cambiado
desde la última ejecución y solo importa lo nuevo.

Diseñado para ejecutarse automáticamente desde el daemon.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.sync")

AGENT_DIR = Path.home() / ".agent"
MEMORY_DIR = AGENT_DIR / "memory"
CORTEX_DIR = Path.home() / ".cortex"
SYNC_STATE_FILE = CORTEX_DIR / "sync_state.json"


# ─── Resultado de la sincronización ──────────────────────────────────


@dataclass
class SyncResult:
    """Resultado de una ronda de sincronización."""

    synced_at: str = ""
    facts_synced: int = 0
    ghosts_synced: int = 0
    errors_synced: int = 0
    bridges_synced: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.facts_synced + self.ghosts_synced + self.errors_synced + self.bridges_synced

    @property
    def had_changes(self) -> bool:
        return self.total > 0


# ─── Estado de sincronización ────────────────────────────────────────


def _load_sync_state() -> dict:
    """Carga el estado de la última sincronización (hashes de archivos)."""
    if SYNC_STATE_FILE.exists():
        try:
            return json.loads(SYNC_STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_sync_state(state: dict) -> None:
    """Guarda el estado de sincronización a disco."""
    SYNC_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SYNC_STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _file_hash(path: Path) -> str:
    """Calcula SHA-256 de un archivo para detectar cambios."""
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ─── Motor principal de sincronización ───────────────────────────────


def sync_memory(engine: CortexEngine) -> SyncResult:
    """Sincroniza ~/.agent/memory/ → CORTEX DB.

    Solo importa archivos que han cambiado desde la última sincronización.
    Usa hashes SHA-256 para detectar cambios. Idempotente y no destructivo.

    Args:
        engine: Instancia inicializada de CortexEngine.

    Returns:
        SyncResult con estadísticas de la sincronización.
    """
    from cortex.temporal import now_iso

    result = SyncResult(synced_at=now_iso())
    state = _load_sync_state()

    if not MEMORY_DIR.exists():
        result.errors.append(f"Directorio de memoria no encontrado: {MEMORY_DIR}")
        return result

    # ── 1. Sincronizar ghosts.json ───────────────────────────────
    ghosts_file = MEMORY_DIR / "ghosts.json"
    try:
        ghosts_hash = _file_hash(ghosts_file)
        if ghosts_hash and ghosts_hash != state.get("ghosts_hash"):
            _sync_ghosts(engine, ghosts_file, result)
            state["ghosts_hash"] = ghosts_hash
    except Exception as e:
        result.errors.append(f"ghosts.json: {e}")
        logger.error("Syncing ghosts failed: %s", e)

    # ── 2. Sincronizar system.json (conocimiento global) ─────────
    system_file = MEMORY_DIR / "system.json"
    try:
        system_hash = _file_hash(system_file)
        if system_hash and system_hash != state.get("system_hash"):
            _sync_system(engine, system_file, result)
            state["system_hash"] = system_hash
    except Exception as e:
        result.errors.append(f"system.json: {e}")
        logger.error("Syncing system failed: %s", e)

    # ── 3. Sincronizar mistakes.jsonl (errores) ──────────────────
    mistakes_file = MEMORY_DIR / "mistakes.jsonl"
    try:
        mistakes_hash = _file_hash(mistakes_file)
        if mistakes_hash and mistakes_hash != state.get("mistakes_hash"):
            _sync_mistakes(engine, mistakes_file, result)
            state["mistakes_hash"] = mistakes_hash
    except Exception as e:
        result.errors.append(f"mistakes.jsonl: {e}")
        logger.error("Syncing mistakes failed: %s", e)

    # ── 4. Sincronizar bridges.jsonl (conexiones entre proyectos)
    bridges_file = MEMORY_DIR / "bridges.jsonl"
    try:
        bridges_hash = _file_hash(bridges_file)
        if bridges_hash and bridges_hash != state.get("bridges_hash"):
            _sync_bridges(engine, bridges_file, result)
            state["bridges_hash"] = bridges_hash
    except Exception as e:
        result.errors.append(f"bridges.jsonl: {e}")
        logger.error("Syncing bridges failed: %s", e)

    # Guardar estado para la próxima ejecución
    state["last_sync"] = result.synced_at
    _save_sync_state(state)

    if result.had_changes:
        logger.info(
            "Sincronización completada: %d hechos nuevos (%d ghosts, %d errores, %d bridges)",
            result.total,
            result.ghosts_synced,
            result.errors_synced,
            result.bridges_synced,
        )
    else:
        logger.debug("Sin cambios detectados desde la última sincronización")

    return result


# ─── Sincronizadores individuales ────────────────────────────────────


def _sync_ghosts(engine: CortexEngine, path: Path, result: SyncResult) -> None:
    """Sincroniza ghosts.json — estado actual de cada proyecto fantasma.

    Depreca los ghosts anteriores y almacena el snapshot actual.
    Así CORTEX siempre tiene el estado más reciente de cada proyecto.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        result.errors.append(f"Error leyendo ghosts.json: {e}")
        return

    # Deprecar ghosts anteriores (son snapshots temporales)
    conn = engine._get_conn()
    try:
        conn.execute(
            "UPDATE facts SET valid_until = ? WHERE fact_type = 'ghost' AND valid_until IS NULL",
            (result.synced_at,),
        )
        conn.commit()
    except sqlite3.Error as e:
        result.errors.append(f"Error deprecando ghosts antiguos: {e}")

    # Insertar snapshot actual de cada proyecto
    for project_name, ghost_data in data.items():
        content = (
            f"GHOST: {project_name} | "
            f"Última tarea: {ghost_data.get('last_task', 'desconocida')} | "
            f"Estado: {ghost_data.get('mood', 'desconocido')} | "
            f"Bloqueado: {ghost_data.get('blocked_by', 'no')}"
        )
        try:
            engine.store(
                project=project_name,
                content=content,
                fact_type="ghost",
                tags=["ghost", "proyecto-estado", ghost_data.get("mood", "")],
                confidence="verified",
                source="sync-agent-memory",
                meta=ghost_data,
                valid_from=ghost_data.get("timestamp"),
            )
            result.ghosts_synced += 1
        except (sqlite3.Error, ValueError) as e:
            result.errors.append(f"Error sincronizando ghost {project_name}: {e}")


def _calculate_fact_diff(existing: set[str], candidates: list[dict], content_generator: Any) -> list[tuple[str, dict]]:
    """Calcula qué hechos son nuevos comparándolos con lo existente."""
    results = []
    for c in candidates:
        content = content_generator(c)
        if content not in existing:
            results.append((content, c))
    return results


def _sync_system(engine: CortexEngine, path: Path, result: SyncResult) -> None:
    """Sincroniza system.json — conocimiento global y decisiones.

    Importa las secciones knowledge_global y decisions_global
    que no existan ya en CORTEX (dedup por contenido).
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        result.errors.append(f"Error leyendo system.json: {e}")
        return

    # Obtener contenidos existentes para dedup
    existing = _get_existing_contents(engine, "__system__")

    # knowledge_global
    kb_candidates = data.get("knowledge_global", [])
    new_kb = _calculate_fact_diff(existing, kb_candidates, lambda x: x.get("content", str(x)))
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
    new_dec = _calculate_fact_diff(existing, dec_candidates, lambda x: f"DECISION: {x.get('decision', str(x))} | RAZON: {x.get('reason', '')}")
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


def _sync_mistakes(engine: CortexEngine, path: Path, result: SyncResult) -> None:
    """Sincroniza mistakes.jsonl — memoria de errores."""
    existing = _get_existing_contents(engine, None, fact_type="error")
    lines = [json.loads(l) for l in path.read_text(encoding="utf-8").strip().splitlines() if l.strip()]
    
    def generate_content(m):
        return (f"ERROR: {m.get('error', 'desconocido')} | "
                f"CAUSA: {m.get('root_cause', 'desconocida')} | "
                f"FIX: {m.get('fix', 'desconocido')}")

    new_mistakes = _calculate_fact_diff(existing, lines, generate_content)
    for content, m in new_mistakes:
        try:
            engine.store(
                project=m.get("project", "__system__"),
                content=content,
                fact_type="error",
                tags=m.get("tags", []),
                confidence="verified",
                source="sync-agent-memory",
                valid_from=m.get("date"),
                meta=m,
            )
            result.errors_synced += 1
            existing.add(content)
        except Exception as e:
            result.errors.append(f"Error sync mistake: {e}")


def _sync_bridges(engine: CortexEngine, path: Path, result: SyncResult) -> None:
    """Sincroniza bridges.jsonl — conexiones entre proyectos."""
    existing = _get_existing_contents(engine, "__bridges__", fact_type="bridge")
    lines = [json.loads(l) for l in path.read_text(encoding="utf-8").strip().splitlines() if l.strip()]

    def generate_content(b):
        return (f"BRIDGE: {b.get('from', '?')} → {b.get('to', '?')} | "
                f"Patrón: {b.get('pattern', '?')} | "
                f"Nota: {b.get('note', '')}")

    new_bridges = _calculate_fact_diff(existing, lines, generate_content)
    for content, b in new_bridges:
        try:
            engine.store(
                project="__bridges__",
                content=content,
                fact_type="bridge",
                tags=[b.get("from", ""), b.get("to", ""), b.get("pattern", "")],
                confidence="verified",
                source="sync-agent-memory",
                valid_from=b.get("date"),
                meta=b,
            )
            result.bridges_synced += 1
            existing.add(content)
        except Exception as e:
            result.errors.append(f"Error sync bridge: {e}")


# ─── Utilidades ──────────────────────────────────────────────────────


def _get_existing_contents(
    engine: CortexEngine,
    project: str | None = None,
    fact_type: str | None = None,
) -> set[str]:
    """Obtiene set de contenidos existentes para deduplicación rápida.

    Args:
        engine: Instancia de CortexEngine.
        project: Filtrar por proyecto. None = todos.
        fact_type: Filtrar por tipo. None = todos.

    Returns:
        Set de strings con el contenido de cada fact existente.
    """
    conn = engine._get_conn()
    query = "SELECT content FROM facts WHERE valid_until IS NULL"
    params: list = []

    if project:
        query += " AND project = ?"
        params.append(project)
    if fact_type:
        query += " AND fact_type = ?"
        params.append(fact_type)

    rows = conn.execute(query, params).fetchall()
    return {row[0] for row in rows}


# ─── Exportación: CORTEX → Markdown (snapshot para el agente) ────────


def export_snapshot(engine: CortexEngine, out_path: Path | None = None) -> Path:
    """Exporta un snapshot legible de toda la memoria activa de CORTEX.

    Genera un archivo markdown que el agente IA puede leer al inicio
    de cada conversación para tener contexto completo.

    Args:
        engine: Instancia de CortexEngine.
        out_path: Ruta de salida. Por defecto ~/.cortex/context-snapshot.md

    Returns:
        Path del archivo generado.
    """
    from cortex.temporal import now_iso

    if out_path is None:
        out_path = CORTEX_DIR / "context-snapshot.md"

    conn = engine._get_conn()
    rows = conn.execute(
        "SELECT project, content, fact_type, tags, confidence "
        "FROM facts WHERE valid_until IS NULL "
        "ORDER BY project, fact_type, id"
    ).fetchall()

    # Agrupar por proyecto
    by_project: dict[str, list] = {}
    for row in rows:
        project = row[0]
        by_project.setdefault(project, []).append({
            "content": row[1],
            "type": row[2],
            "tags": json.loads(row[3]) if row[3] else [],
            "confidence": row[4],
        })

    lines = [
        "# 🧠 CORTEX — Snapshot de Memoria",
        "",
        f"> Generado automáticamente: {now_iso()}",
        f"> Total: {len(rows)} facts activos en {len(by_project)} proyectos",
        "",
    ]

    stats = engine.stats()
    lines.extend([
        "## Estado del Sistema",
        "",
        f"- **DB:** {stats['db_path']} ({stats['db_size_mb']} MB)",
        f"- **Facts activos:** {stats['active_facts']}",
        f"- **Proyectos:** {', '.join(stats['projects'])}",
        f"- **Tipos:** {', '.join(f'{t}: {c}' for t, c in stats['types'].items())}",
        "",
    ])

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


# ─── Write-back: CORTEX → JSON (sincronización inversa) ─────────────
#
# Modelo mental: CORTEX DB es la fuente de verdad (Source of Truth).
# Los archivos JSON son una "proyección" legible de la DB.
#
# Flujo:
# 1. Calcular SHA-256 del estado actual en DB para cada target file
# 2. Comparar con SHA almacenado de la última exportación
# 3. Solo escribir si hay cambio real
# 4. Escritura atómica: tempfile + os.replace() para evitar corrupción
#

# Mapeo de fact_type → archivo destino
_WRITEBACK_MAP = {
    "ghost":     "ghosts.json",
    "knowledge": "system.json",
    "decision":  "system.json",
    "error":     "mistakes.jsonl",
    "bridge":    "bridges.jsonl",
}


@dataclass
class WritebackResult:
    """Resultado de una ronda de write-back."""

    files_written: int = 0
    files_skipped: int = 0
    items_exported: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def had_changes(self) -> bool:
        return self.files_written > 0


def _db_content_hash(engine: CortexEngine, fact_type: str | None = None) -> str:
    """Calcula SHA-256 del contenido actual en DB para un tipo de fact.

    Esto permite detectar si la DB ha cambiado desde el último write-back
    sin necesidad de comparar fila por fila.
    """
    conn = engine._get_conn()
    if fact_type:
        rows = conn.execute(
            "SELECT id, content, meta, valid_from FROM facts "
            "WHERE fact_type = ? AND valid_until IS NULL ORDER BY id",
            (fact_type,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, content, meta, valid_from FROM facts "
            "WHERE valid_until IS NULL ORDER BY id"
        ).fetchall()

    # Serializar todo el contenido como un hash determinista
    hasher = hashlib.sha256()
    for row in rows:
        hasher.update(f"{row[0]}|{row[1]}|{row[2]}|{row[3]}\n".encode("utf-8"))
    return hasher.hexdigest()


def _atomic_write(path: Path, content: str) -> None:
    """Escritura atómica: escribe a temp + os.replace().

    Evita corrupción si el proceso muere a mitad de escritura.
    En POSIX, os.replace() es atómico dentro del mismo filesystem.
    """
    # tempfile and os imported at module level

    path.parent.mkdir(parents=True, exist_ok=True)
    # Crear temp en el mismo directorio para garantizar mismo filesystem
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(path))
    except OSError:
        # Limpiar temp si falla el replace
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


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
    from cortex.temporal import now_iso

    result = WritebackResult()
    state = _load_sync_state()
    wb_hashes = state.get("writeback_hashes", {})

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. Ghosts → ghosts.json ──────────────────────────────────
    try:
        db_hash = _db_content_hash(engine, "ghost")
        if db_hash != wb_hashes.get("ghost"):
            _writeback_ghosts(engine, result)
            wb_hashes["ghost"] = db_hash
        else:
            result.files_skipped += 1
    except Exception as e:
        result.errors.append(f"ghost: {e}")
        logger.exception("Write-back ghosts failed")

    # ── 2. System (knowledge + decisions) → system.json ──────────
    try:
        k_hash = _db_content_hash(engine, "knowledge")
        d_hash = _db_content_hash(engine, "decision")
        combined_hash = hashlib.sha256(f"{k_hash}:{d_hash}".encode()).hexdigest()
        if combined_hash != wb_hashes.get("system"):
            _writeback_system(engine, result)
            wb_hashes["system"] = combined_hash
        else:
            result.files_skipped += 1
    except Exception as e:
        result.errors.append(f"system: {e}")
        logger.exception("Write-back system failed")

    # ── 3. Mistakes → mistakes.jsonl ─────────────────────────────
    try:
        db_hash = _db_content_hash(engine, "error")
        if db_hash != wb_hashes.get("error"):
            _writeback_mistakes(engine, result)
            wb_hashes["error"] = db_hash
        else:
            result.files_skipped += 1
    except Exception as e:
        result.errors.append(f"error: {e}")
        logger.exception("Write-back mistakes failed")

    # ── 4. Bridges → bridges.jsonl ───────────────────────────────
    try:
        db_hash = _db_content_hash(engine, "bridge")
        if db_hash != wb_hashes.get("bridge"):
            _writeback_bridges(engine, result)
            wb_hashes["bridge"] = db_hash
        else:
            result.files_skipped += 1
    except Exception as e:
        result.errors.append(f"bridge: {e}")
        logger.exception("Write-back bridges failed")

    # Guardar hashes para la próxima ejecución
    state["writeback_hashes"] = wb_hashes
    state["last_writeback"] = now_iso()
    _save_sync_state(state)

    if result.had_changes:
        logger.info(
            "Write-back completado: %d archivos actualizados, %d items exportados",
            result.files_written, result.items_exported,
        )
    else:
        logger.debug("Write-back: sin cambios en DB desde la última exportación")

    return result


# ─── Write-back individuales ────────────────────────────────────────


def _writeback_ghosts(engine: CortexEngine, result: WritebackResult) -> None:
    """Reconstruye ghosts.json desde facts tipo 'ghost'."""
    conn = engine._get_conn()
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
    _atomic_write(MEMORY_DIR / "ghosts.json", content)

    result.files_written += 1
    result.items_exported += len(ghosts)
    logger.info("Write-back ghosts: %d proyectos", len(ghosts))


def _writeback_system(engine: CortexEngine, result: WritebackResult) -> None:
    """Reconstruye system.json desde facts tipo 'knowledge' y 'decision'."""
    from cortex.temporal import now_iso
    conn = engine._get_conn()

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
        knowledge_list.append({
            "id": meta.get("id", f"K{len(knowledge_list) + 1:03d}"),
            "topic": meta.get("topic", "general"),
            "content": row[0],
            "added": row[3] or "",
            "confidence": row[2] or "stated",
        })

    # Decisions global — reconstruir desde DB
    d_rows = conn.execute(
        "SELECT content, meta FROM facts "
        "WHERE project = '__system__' AND fact_type = 'decision' "
        "AND valid_until IS NULL ORDER BY id"
    ).fetchall()

    decisions_list = []
    for row in d_rows:
        meta = json.loads(row[1]) if row[1] else {}
        decisions_list.append({
            "id": meta.get("id", f"D{len(decisions_list) + 1:03d}"),
            "decision": row[0],
            **{k: v for k, v in meta.items() if k != "id"},
        })

    system_data["knowledge_global"] = knowledge_list
    system_data["decisions_global"] = decisions_list
    system_data.setdefault("meta", {})["last_updated"] = now_iso()

    content = json.dumps(system_data, indent=2, ensure_ascii=False)
    _atomic_write(system_path, content)

    count = len(knowledge_list) + len(decisions_list)
    result.files_written += 1
    result.items_exported += count
    logger.info("Write-back system: %d knowledge + %d decisions", len(knowledge_list), len(decisions_list))


def _writeback_mistakes(engine: CortexEngine, result: WritebackResult) -> None:
    """Reconstruye mistakes.jsonl desde facts tipo 'error'."""
    conn = engine._get_conn()
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
    _atomic_write(MEMORY_DIR / "mistakes.jsonl", content)

    result.files_written += 1
    result.items_exported += len(lines)
    logger.info("Write-back mistakes: %d errores", len(lines))


def _writeback_bridges(engine: CortexEngine, result: WritebackResult) -> None:
    """Reconstruye bridges.jsonl desde facts tipo 'bridge'."""
    conn = engine._get_conn()
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
    _atomic_write(MEMORY_DIR / "bridges.jsonl", content)

    result.files_written += 1
    result.items_exported += len(lines)
    logger.info("Write-back bridges: %d bridges", len(lines))


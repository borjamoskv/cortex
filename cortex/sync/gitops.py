"""CORTEX GitOps Memory — Synchronizes global facts to local repository JSON/MD files."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.sync.gitops")

def _locate_repo_root(project_name: str) -> Path | None:
    """Intenta localizar la carpeta del proyecto en rutas estándar."""
    game_dir = Path.home() / "game" / project_name
    if game_dir.exists() and game_dir.is_dir():
        return game_dir
    # Se podrían añadir más heurísticas aquí (e.g. buscar en ~/Developer, etc.)
    return None

def _get_cortex_dir(repo_path: Path) -> Path:
    cortex_dir = repo_path / ".cortex"
    cortex_dir.mkdir(parents=True, exist_ok=True)
    return cortex_dir

def _load_knowledge(json_path: Path) -> dict:
    if json_path.exists():
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, KeyError):
            return {"facts": []}
    return {"facts": []}

def sync_fact_to_repo(project: str, fact_id: int, fact_data: dict[str, Any], action: str = "upsert") -> bool:
    """
    Sincroniza un fact (creación, edición, borrado silente) con el JSON local del proyecto.
    action puede ser 'upsert' o 'deprecate'.
    Se asume que esto se llama *después* de que SQLite haya hecho commit (o se está seguro).
    """
    repo_path = _locate_repo_root(project)
    if not repo_path:
        return False
        
    try:
        cortex_dir = _get_cortex_dir(repo_path)
        json_path = cortex_dir / "knowledge.json"
        
        # 1. Cargar el JSON actual o crear nuevo
        knowledge = _load_knowledge(json_path)
            
        facts_list = knowledge.get("facts", [])
        
        # 2. Modificar la lista
        existing_idx = next((i for i, f in enumerate(facts_list) if f.get("id") == fact_id), None)
        
        if action == "upsert":
            if existing_idx is not None:
                facts_list[existing_idx] = fact_data
            else:
                facts_list.append(fact_data)
        elif action == "deprecate" and existing_idx is not None:
            facts_list[existing_idx]["valid_until"] = fact_data.get("valid_until", "deprecated")
            if "meta" in fact_data:
                facts_list[existing_idx]["meta"] = fact_data["meta"]
                    
        knowledge["facts"] = facts_list
        
        # 3. Escribir JSON atómicamente (o casi, para nuestro caso de uso local es suficiente)
        json_path.write_text(json.dumps(knowledge, indent=2, ensure_ascii=False), encoding="utf-8")
        
        # 4. Renderizar Markdown snapshot
        _render_snapshot(cortex_dir, facts_list, project)
        return True
        
    except (OSError, ValueError, KeyError) as e:
        logger.error(f"Failed to sync GitOps memory for {project}: {e}")
        return False

def _render_snapshot(cortex_dir: Path, facts_list: list[dict[str, Any]], project: str) -> None:
    """Genera un Markdown legible a partir del JSON de facts."""
    md_path = cortex_dir / "context-snapshot.md"
    
    # Filtrar activos y ordenar por fecha descendente
    active_facts = [f for f in facts_list if not f.get("valid_until")]
    active_facts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    lines = [
        f"# CORTEX Snapshot: {project}",
        "",
        "> **Sovereign GitOps Memory**",
        "> Generado automáticamente a partir de `knowledge.json`. No editar a mano.",
        "",
        f"Total hechos activos: **{len(active_facts)}**",
        ""
    ]
    
    
    # Agrupar por type
    by_type = {}
    for fact in active_facts:
        ftype = fact.get("fact_type", "knowledge")
        by_type.setdefault(ftype, []).append(fact)
        
    for ftype, items in by_type.items():
        lines.append(f"## {ftype.upper()}")
        lines.append("")
        for fact in items:
            date_str = fact.get("created_at", "N/A")[:10]
            conf = fact.get("confidence", "stated")
            lines.append(f"### [#{fact.get('id')}] ({date_str}) - {conf.upper()}")
            lines.append(f"{fact.get('content')}")
            if fact.get("tags"):
                lines.append(f"*Tags: {', '.join(fact.get('tags'))}*")
            lines.append("")
            
    md_path.write_text("\n".join(lines), encoding="utf-8")

def export_gitops_memory(engine, project: str) -> bool:
    """Regenera la carpeta .cortex/ y los archivos knowledge.json y context-snapshot.md desde SQLite."""
    repo_path = _locate_repo_root(project)
    if not repo_path:
        logger.error(f"Cannot export: project directory not found for {project}")
        return False
        
    cortex_dir = _get_cortex_dir(repo_path)
    json_path = cortex_dir / "knowledge.json"
    
    try:
        facts = engine.recall_sync(project)
        import dataclasses
        facts_list = []
        for f in facts:
            fact_data = dataclasses.asdict(f)
            # rename id to match JSON format
            fact_data["id"] = fact_data.pop("fact_id", fact_data.get("id"))
            if fact_data.get("valid_from") and isinstance(fact_data["valid_from"], str):
                # Ensure date format
                fact_data["created_at"] = fact_data["valid_from"]
            facts_list.append(fact_data)
            
        knowledge = {"facts": facts_list}
        json_path.write_text(json.dumps(knowledge, indent=2, ensure_ascii=False), encoding="utf-8")
        _render_snapshot(cortex_dir, facts_list, project)
        return True
    except (OSError, ValueError, KeyError) as e:
        logger.error(f"Export fell down: {e}")
        return False

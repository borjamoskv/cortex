"""Graph Processing Engine.

Extraction, relationship detection, and backend orchestration.
"""
import sqlite3
from typing import Optional

from cortex.config import GRAPH_BACKEND
from cortex.graph.backends import GraphBackend, Neo4jBackend, SQLiteBackend
from cortex.graph.patterns import COMMON_WORDS, ENTITY_PATTERNS, RELATION_SIGNALS


def get_backend(conn: Optional[sqlite3.Connection] = None) -> GraphBackend:
    if GRAPH_BACKEND == "neo4j":
        return Neo4jBackend()
    return SQLiteBackend(conn)  # type: ignore


def extract_entities(content: str) -> list[dict]:
    if not content or not content.strip(): return []
    seen = set(); entities = []
    for entity_type, pattern in ENTITY_PATTERNS:
        for match in pattern.finditer(content):
            name = match.group(1).strip()
            name_lower = name.lower()
            if len(name) < 2 or len(name) > 100 or name_lower in seen: continue
            if entity_type == "project" and name_lower in COMMON_WORDS: continue
            seen.add(name_lower)
            entities.append({"name": name, "entity_type": entity_type})
    return entities


def detect_relationships(content: str, entities: list[dict]) -> list[dict]:
    if len(entities) < 2: return []
    relationships = []; content_lower = content.lower()
    detected_relation = "related_to"
    for relation_type, signals in RELATION_SIGNALS.items():
        for signal in signals:
            if signal in content_lower:
                detected_relation = relation_type
                break
        if detected_relation != "related_to": break
    for i, source in enumerate(entities):
        for target in entities[i+1:]:
            if source["name"].lower() == target["name"].lower(): continue
            relationships.append({"source_name": source["name"], "target_name": target["name"], "relation_type": detected_relation})
    return relationships


def process_fact_graph(conn: sqlite3.Connection, fact_id: int, content: str, project: str, timestamp: str) -> tuple[int, int]:
    entities = extract_entities(content)
    if not entities: return 0, 0
    relationships = detect_relationships(content, entities)
    
    # Dual-Write Strategy
    backends: list[GraphBackend] = [SQLiteBackend(conn)]
    if GRAPH_BACKEND == "neo4j":
        backends.append(Neo4jBackend())
    
    total_added_entities = 0
    total_added_rels = 0
    
    try:
        for backend in backends:
            entity_ids = {}
            for ent in entities:
                eid = backend.upsert_entity(ent["name"], ent["entity_type"], project, timestamp)
                entity_ids[ent["name"]] = eid
            
            for rel in relationships:
                sid = entity_ids.get(rel["source_name"])
                tid = entity_ids.get(rel["target_name"])
                if sid and tid:
                    backend.upsert_relationship(sid, tid, rel["relation_type"], fact_id, timestamp)
        
        return len(entities), len(relationships)
    except (sqlite3.Error, Exception):
        return 0, 0


def get_graph(conn: sqlite3.Connection, project: Optional[str] = None, limit: int = 50) -> dict:
    return get_backend(conn).get_graph(project, limit)


def query_entity(conn: sqlite3.Connection, name: str, project: Optional[str] = None) -> Optional[dict]:
    return get_backend(conn).query_entity(name, project)

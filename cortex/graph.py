"""
CORTEX v4.1 — Graph Memory (Multi-Backend).

Lightweight knowledge graph built from stored facts.
Supports SQLite (local) and Neo4j (global ecosystem) backends.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple

from cortex.config import GRAPH_BACKEND, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger("cortex.graph")

__all__ = [
    "Entity",
    "Relationship",
    "GraphBackend",
    "SQLiteBackend",
    "Neo4jBackend",
    "extract_entities",
    "detect_relationships",
    "process_fact_graph",
    "get_graph",
    "query_entity",
    "get_backend",
]

# ─── Data Models ─────────────────────────────────────────────────────

@dataclass
class Entity:
    """A named entity extracted from facts."""
    id: int | str = 0
    name: str = ""
    entity_type: str = "unknown"
    project: str = ""
    first_seen: str = ""
    last_seen: str = ""
    mention_count: int = 1
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.entity_type,
            "project": self.project,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "mentions": self.mention_count,
        }

@dataclass
class Relationship:
    """A relationship between two entities."""
    id: int | str = 0
    source_entity_id: int | str = 0
    target_entity_id: int | str = 0
    relation_type: str = "related_to"
    weight: float = 1.0
    first_seen: str = ""
    source_fact_id: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source_entity_id,
            "target": self.target_entity_id,
            "type": self.relation_type,
            "weight": self.weight,
        }

@dataclass
class Ghost:
    """A dangling reference that needs resolution."""
    id: int | str = 0
    reference: str = ""
    context: str = ""
    project: str = ""
    status: str = "open" # open, resolved, pending_review
    detected_at: str = ""
    resolved_at: Optional[str] = None
    target_id: Optional[int | str] = None
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "reference": self.reference,
            "project": self.project,
            "status": self.status,
            "confidence": self.confidence,
            "target_id": self.target_id
        }

# ─── Abstract Backend ────────────────────────────────────────────────

class GraphBackend(ABC):
    @abstractmethod
    def upsert_entity(self, name: str, entity_type: str, project: str, timestamp: str) -> int | str:
        pass

    @abstractmethod
    def upsert_relationship(self, source_id: int | str, target_id: int | str, relation_type: str, fact_id: int, timestamp: str) -> int | str:
        pass

    @abstractmethod
    def get_graph(self, project: Optional[str] = None, limit: int = 50) -> dict:
        pass

    @abstractmethod
    def query_entity(self, name: str, project: Optional[str] = None) -> Optional[dict]:
        pass

    @abstractmethod
    def upsert_ghost(self, reference: str, context: str, project: str, timestamp: str) -> int | str:
        pass

    @abstractmethod
    def resolve_ghost(self, ghost_id: int | str, target_id: int | str, confidence: float, timestamp: str) -> bool:
        pass

# ─── SQLite Backend ──────────────────────────────────────────────────

class SQLiteBackend(GraphBackend):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def upsert_entity(self, name: str, entity_type: str, project: str, timestamp: str) -> int:
        row = self.conn.execute(
            "SELECT id, mention_count FROM entities WHERE name = ? AND project = ?",
            (name, project),
        ).fetchone()

        if row:
            entity_id, count = row
            self.conn.execute(
                "UPDATE entities SET mention_count = ?, last_seen = ? WHERE id = ?",
                (count + 1, timestamp, entity_id),
            )
            return entity_id
        else:
            cursor = self.conn.execute(
                """INSERT INTO entities (name, entity_type, project, first_seen, last_seen, mention_count)
                   VALUES (?, ?, ?, ?, ?, 1)""",
                (name, entity_type, project, timestamp, timestamp),
            )
            return cursor.lastrowid

    def upsert_relationship(self, source_id: int, target_id: int, relation_type: str, fact_id: int, timestamp: str) -> int:
        row = self.conn.execute(
            "SELECT id, weight FROM entity_relations "
            "WHERE source_entity_id = ? AND target_entity_id = ?",
            (source_id, target_id),
        ).fetchone()

        if row:
            rel_id, weight = row
            self.conn.execute(
                "UPDATE entity_relations SET weight = ?, relation_type = ? WHERE id = ?",
                (weight + 0.5, relation_type, rel_id),
            )
            return rel_id
        else:
            cursor = self.conn.execute(
                """INSERT INTO entity_relations
                   (source_entity_id, target_entity_id, relation_type, weight, first_seen, source_fact_id)
                   VALUES (?, ?, ?, 1.0, ?, ?)""",
                (source_id, target_id, relation_type, timestamp, fact_id),
            )
            return cursor.lastrowid

    def get_graph(self, project: Optional[str] = None, limit: int = 50) -> dict:
        # Implementation moved from original get_graph
        if project:
            entity_rows = self.conn.execute(
                "SELECT id, name, entity_type, project, first_seen, last_seen, mention_count "
                "FROM entities WHERE project = ? ORDER BY mention_count DESC LIMIT ?",
                (project, limit),
            ).fetchall()
        else:
            entity_rows = self.conn.execute(
                "SELECT id, name, entity_type, project, first_seen, last_seen, mention_count "
                "FROM entities ORDER BY mention_count DESC LIMIT ?",
                (limit,),
            ).fetchall()

        entities = []
        entity_ids = set()
        for row in entity_rows:
            entity_ids.add(row[0])
            entities.append({
                "id": row[0], "name": row[1], "type": row[2], "project": row[3],
                "first_seen": row[4], "last_seen": row[5], "mentions": row[6],
            })

        if entity_ids:
            placeholders = ",".join("?" * len(entity_ids))
            id_list = list(entity_ids)
            rel_rows = self.conn.execute(
                "SELECT id, source_entity_id, target_entity_id, relation_type, weight "
                "FROM entity_relations "
                "WHERE source_entity_id IN (" + placeholders + ") "
                "OR target_entity_id IN (" + placeholders + ")",
                id_list + id_list,
            ).fetchall()
        else:
            rel_rows = []

        relationships = []
        for row in rel_rows:
            relationships.append({
                "id": row[0], "source": row[1], "target": row[2],
                "type": row[3], "weight": row[4],
            })

        # Stats
        if project:
            total_entities = self.conn.execute(
                "SELECT COUNT(*) FROM entities WHERE project = ?", (project,)
            ).fetchone()[0]
            # Approximate rel count by source entity project
            total_rels = self.conn.execute(
                """SELECT COUNT(*) FROM entity_relations er
                   JOIN entities e ON er.source_entity_id = e.id
                   WHERE e.project = ?""", (project,)
            ).fetchone()[0]
        else:
            total_entities = self.conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            total_rels = self.conn.execute("SELECT COUNT(*) FROM entity_relations").fetchone()[0]

        return {
            "entities": entities,
            "relationships": relationships,
            "stats": {
                "total_entities": total_entities,
                "total_relationships": total_rels
            }
        }

    def query_entity(self, name: str, project: Optional[str] = None) -> Optional[dict]:
        if not name or not name.strip(): return None
        if project:
            row = self.conn.execute(
                "SELECT id, name, entity_type, project, first_seen, last_seen, mention_count "
                "FROM entities WHERE name = ? AND project = ?",
                (name, project),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT id, name, entity_type, project, first_seen, last_seen, mention_count "
                "FROM entities WHERE name = ? ORDER BY mention_count DESC LIMIT 1",
                (name,),
            ).fetchone()

        if not row: return None

        entity = {
            "id": row[0], "name": row[1], "type": row[2], "project": row[3],
            "first_seen": row[4], "last_seen": row[5], "mentions": row[6],
        }

        connections = self.conn.execute(
            """SELECT e.name, e.entity_type, er.relation_type, er.weight
               FROM entity_relations er
               JOIN entities e ON (
                   CASE WHEN er.source_entity_id = ? THEN er.target_entity_id
                        ELSE er.source_entity_id END = e.id
               )
               WHERE er.source_entity_id = ? OR er.target_entity_id = ?
               ORDER BY er.weight DESC LIMIT 20""",
            (row[0], row[0], row[0]),
        ).fetchall()

        entity["connections"] = [
            {"name": c[0], "type": c[1], "relation": c[2], "weight": c[3]}
            for c in connections
        ]
        return entity

    def upsert_ghost(self, reference: str, context: str, project: str, timestamp: str) -> int:
        row = self.conn.execute(
            "SELECT id FROM ghosts WHERE reference = ? AND project = ? AND status = 'open'",
            (reference, project),
        ).fetchone()

        if row:
            return row[0]
        else:
            cursor = self.conn.execute(
                """INSERT INTO ghosts (reference, context, project, detected_at, status)
                   VALUES (?, ?, ?, ?, 'open')""",
                (reference, context, project, timestamp),
            )
            return cursor.lastrowid

    def resolve_ghost(self, ghost_id: int, target_id: int, confidence: float, timestamp: str) -> bool:
        cursor = self.conn.execute(
            "UPDATE ghosts SET status = 'resolved', resolved_at = ?, target_id = ?, confidence = ? WHERE id = ?",
            (timestamp, target_id, confidence, ghost_id),
        )
        return cursor.rowcount > 0

# ─── Neo4j Backend ───────────────────────────────────────────────────

class Neo4jBackend(GraphBackend):
    def __init__(self):
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            self._initialized = True
        except ImportError:
            logger.warning("neo4j driver not installed. Neo4jBackend disabled.")
            self._initialized = False
        except Exception as e:
            logger.warning("Failed to connect to Neo4j: %s", e)
            self._initialized = False

    def upsert_entity(self, name: str, entity_type: str, project: str, timestamp: str) -> str:
        if not self._initialized: return ""
        
        query = """
        MERGE (e:Entity {name: $name, project: $project})
        ON CREATE SET e.type = $type, e.first_seen = $ts, e.last_seen = $ts, e.mentions = 1
        ON MATCH SET e.last_seen = $ts, e.mentions = e.mentions + 1
        RETURN id(e) as id
        """
        with self.driver.session() as session:
            result = session.run(query, name=name, project=project, type=entity_type, ts=timestamp)
            record = result.single()
            return str(record["id"]) if record else ""

    def upsert_relationship(self, source_id: str, target_id: str, relation_type: str, fact_id: int, timestamp: str) -> str:
        if not self._initialized: return ""
        
        # In Cypher, relationship types must be alphanumeric. We normalize relation_type.
        rel_type = re.sub(r'[^a-zA-Z0-9_]', '_', relation_type.upper())
        query = f"""
        MATCH (s) WHERE id(s) = toInteger($sid)
        MATCH (t) WHERE id(t) = toInteger($tid)
        MERGE (s)-[r:{rel_type}]->(t)
        ON CREATE SET r.weight = 1.0, r.first_seen = $ts, r.fact_id = $fid
        ON MATCH SET r.weight = r.weight + 0.5
        RETURN id(r) as id
        """
        with self.driver.session() as session:
            result = session.run(query, sid=source_id, tid=target_id, ts=timestamp, fid=fact_id)
            record = result.single()
            return str(record["id"]) if record else ""

    def get_graph(self, project: Optional[str] = None, limit: int = 50) -> dict:
        if not self._initialized: return {"entities": [], "relationships": []}
        
        query = "MATCH (e:Entity) "
        if project: query += "WHERE e.project = $project "
        query += "RETURN e ORDER BY e.mentions DESC LIMIT $limit"
        
        entities = []
        with self.driver.session() as session:
            result = session.run(query, project=project, limit=limit)
            for record in result:
                node = record["e"]
                entities.append({
                    "id": node.id,
                    "name": node["name"],
                    "type": node["type"],
                    "project": node["project"],
                    "mentions": node["mentions"]
                })
        
        # Simplified: for now just return nodes. Relationships can be fetched pairwise.
        return {"entities": entities, "relationships": []}

    def query_entity(self, name: str, project: Optional[str] = None) -> Optional[dict]:
        if not self._initialized: return None
        
        query = "MATCH (e:Entity {name: $name"
        if project: query += ", project: $project"
        query += "}) RETURN e LIMIT 1"
        
        with self.driver.session() as session:
            result = session.run(query, name=name, project=project)
            record = result.single()
            if not record: return None
            node = record["e"]
            entity = {
                "id": node.id, "name": node["name"], "type": node["type"],
                "project": node["project"], "mentions": node["mentions"]
            }
            # Add basic Cypher connection fetch here later if needed
            entity["connections"] = [] 
            return entity

# ─── Entity Type Patterns ───────────────────────────────────────────

ENTITY_PATTERNS = [
    ("file", re.compile(r"(?:^|[\s`\"\'])([a-zA-Z_][\w]*\.(?:py|js|ts|tsx|jsx|css|html|md|yml|yaml|json|toml|rs|go|sql))\b")),
    ("class", re.compile(r"\b([A-Z][a-zA-Z0-9]{2,}(?:[A-Z][a-z]+)+)\b")),
    ("tool", re.compile(r"\b(SQLite|FastAPI|Redis|Docker|Kubernetes|PostgreSQL|MySQL|React|Vue|Next\.js|Vite|Tailwind|Python|TypeScript|JavaScript|GitHub|GitLab|AWS|GCP|Azure|Vercel|Netlify|OpenAI|Anthropic|Claude|GPT|LangChain|LlamaIndex|Mem0|Zep|Letta|MemGPT|Cognee|pytest|uvicorn|pip|npm|node|cargo|sqlite-vec|sentence-transformers|ONNX|MCP)\b", re.IGNORECASE)),
    ("url", re.compile(r"(https?://[^\s<>\"']+|[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-z]{2,})")),
    ("project", re.compile(r"\b([a-z][a-z0-9]*(?:-[a-z0-9]+){1,})\b")),
]

RELATION_SIGNALS = {
    "uses": ["uses", "using", "used", "with", "via", "through"],
    "depends_on": ["depends on", "requires", "needs", "dependency"],
    "created_by": ["created by", "built by", "made by", "authored by", "written by"],
    "replaces": ["replaces", "replaced", "instead of", "migrated from"],
    "extends": ["extends", "inherits", "based on", "derived from"],
    "contains": ["contains", "includes", "has", "with"],
    "deployed_to": ["deployed to", "hosted on", "runs on", "deployed on"],
    "integrates": ["integrates with", "connects to", "integrated"],
}

_COMMON_WORDS = frozenset({
    "how-to", "set-up", "built-in", "run-time", "self-hosted", "up-to", "opt-in", "opt-out", "plug-in", "add-on",
    "on-premise", "on-prem", "re-run", "re-use", "pre-built", "well-known", "long-term", "short-term", "real-time",
    "open-source", "third-party", "end-to", "out-of", "read-only", "write-only", "read-write", "day-to", "step-by",
    "one-to", "many-to", "high-level", "low-level", "top-level", "the-end", "to-do", "per-day", "per-hour",
    "day-one", "end-of", "on-the", "in-the", "at-the", "by-the", "for-the", "non-null", "non-empty", "pre-commit", "post-commit",
})

# ─── Global Helpers ──────────────────────────────────────────────────

def get_backend(conn: Optional[sqlite3.Connection] = None) -> GraphBackend:
    if GRAPH_BACKEND == "neo4j":
        return Neo4jBackend()
    return SQLiteBackend(conn)

def extract_entities(content: str) -> list[dict]:
    if not content or not content.strip(): return []
    seen = set(); entities = []
    for entity_type, pattern in ENTITY_PATTERNS:
        for match in pattern.finditer(content):
            name = match.group(1).strip()
            name_lower = name.lower()
            if len(name) < 2 or len(name) > 100 or name_lower in seen: continue
            if entity_type == "project" and name_lower in _COMMON_WORDS: continue
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
    backends = [SQLiteBackend(conn)]
    if GRAPH_BACKEND == "neo4j":
        backends.append(Neo4jBackend())
    
    total_added_entities = 0
    total_added_rels = 0
    
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

def get_graph(conn: sqlite3.Connection, project: Optional[str] = None, limit: int = 50) -> dict:
    return get_backend(conn).get_graph(project, limit)

def query_entity(conn: sqlite3.Connection, name: str, project: Optional[str] = None) -> Optional[dict]:
    return get_backend(conn).query_entity(name, project)


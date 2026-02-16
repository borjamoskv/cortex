"""Graph Storage Backends.

Abstract base class and implementations for SQLite (local) and Neo4j (global).
"""
import logging
import re
import sqlite3
from abc import ABC, abstractmethod
from typing import Optional

from cortex.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger("cortex.graph.backends")

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

    def resolve_ghost(self, ghost_id: int | str, target_id: int | str, confidence: float, timestamp: str) -> bool:
        cursor = self.conn.execute(
            "UPDATE ghosts SET status = 'resolved', resolved_at = ?, target_id = ?, confidence = ? WHERE id = ?",
            (timestamp, target_id, confidence, ghost_id),
        )
        return cursor.rowcount > 0


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

    def upsert_relationship(self, source_id: int | str, target_id: int | str, relation_type: str, fact_id: int, timestamp: str) -> str:
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

    def upsert_ghost(self, reference: str, context: str, project: str, timestamp: str) -> str:
        if not self._initialized: return ""
        
        query = """
        MERGE (g:Ghost {reference: $ref, project: $proj})
        ON CREATE SET g.context = $ctx, g.detected_at = $ts, g.status = 'open'
        RETURN id(g) as id
        """
        with self.driver.session() as session:
            result = session.run(query, ref=reference, proj=project, ctx=context, ts=timestamp)
            record = result.single()
            return str(record["id"]) if record else ""

    def resolve_ghost(self, ghost_id: int | str, target_id: int | str, confidence: float, timestamp: str) -> bool:
        if not self._initialized: return False
        
        query = """
        MATCH (g:Ghost) WHERE id(g) = toInteger($gid)
        SET g.status = 'resolved', g.resolved_at = $ts, g.target_id = $tid, g.confidence = $conf
        RETURN count(g) as updated
        """
        with self.driver.session() as session:
            result = session.run(query, gid=ghost_id, tid=target_id, conf=confidence, ts=timestamp)
            record = result.single()
            return record["updated"] > 0 if record else False

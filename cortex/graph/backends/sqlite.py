"""SQLite Graph Backend."""
import logging
import aiosqlite
from typing import Optional
from .base import GraphBackend

logger = logging.getLogger("cortex.graph.backends")

class SQLiteBackend(GraphBackend):
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def upsert_entity(self, name: str, entity_type: str, project: str, timestamp: str) -> int:
        async with self.conn.execute(
            "SELECT id, mention_count FROM entities WHERE name = ? AND project = ?",
            (name, project),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            entity_id, count = row
            await self.conn.execute(
                "UPDATE entities SET mention_count = ?, last_seen = ? WHERE id = ?",
                (count + 1, timestamp, entity_id),
            )
            return entity_id
        else:
            async with self.conn.execute(
                """INSERT INTO entities (name, entity_type, project, first_seen, last_seen, mention_count)
                   VALUES (?, ?, ?, ?, ?, 1)""",
                (name, entity_type, project, timestamp, timestamp),
            ) as cursor:
                return cursor.lastrowid

    async def upsert_relationship(self, source_id: int, target_id: int, relation_type: str, fact_id: int, timestamp: str) -> int:
        async with self.conn.execute(
            "SELECT id, weight FROM entity_relations "
            "WHERE source_entity_id = ? AND target_entity_id = ?",
            (source_id, target_id),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            rel_id, weight = row
            await self.conn.execute(
                "UPDATE entity_relations SET weight = ?, relation_type = ? WHERE id = ?",
                (weight + 0.5, relation_type, rel_id),
            )
            return rel_id
        else:
            async with self.conn.execute(
                """INSERT INTO entity_relations
                   (source_entity_id, target_entity_id, relation_type, weight, first_seen, source_fact_id)
                   VALUES (?, ?, ?, 1.0, ?, ?)""",
                (source_id, target_id, relation_type, timestamp, fact_id),
            ) as cursor:
                return cursor.lastrowid

    async def get_graph(self, project: Optional[str] = None, limit: int = 50) -> dict:
        if project:
            async with self.conn.execute(
                "SELECT id, name, entity_type, project, first_seen, last_seen, mention_count "
                "FROM entities WHERE project = ? ORDER BY mention_count DESC LIMIT ?",
                (project, limit),
            ) as cursor:
                entity_rows = await cursor.fetchall()
        else:
            async with self.conn.execute(
                "SELECT id, name, entity_type, project, first_seen, last_seen, mention_count "
                "FROM entities ORDER BY mention_count DESC LIMIT ?",
                (limit,),
            ) as cursor:
                entity_rows = await cursor.fetchall()

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
            async with self.conn.execute(
                "SELECT id, source_entity_id, target_entity_id, relation_type, weight "
                "FROM entity_relations "
                "WHERE source_entity_id IN (" + placeholders + ") "
                "OR target_entity_id IN (" + placeholders + ")",
                id_list + id_list,
            ) as cursor:
                rel_rows = await cursor.fetchall()
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
            async with self.conn.execute(
                "SELECT COUNT(*) FROM entities WHERE project = ?", (project,)
            ) as cursor:
                row = await cursor.fetchone()
                total_entities = row[0] if row else 0
            
            async with self.conn.execute(
                """SELECT COUNT(*) FROM entity_relations er
                   JOIN entities e ON er.source_entity_id = e.id
                   WHERE e.project = ?""", (project,)
            ) as cursor:
                row = await cursor.fetchone()
                total_rels = row[0] if row else 0
        else:
            async with self.conn.execute("SELECT COUNT(*) FROM entities") as cursor:
                row = await cursor.fetchone()
                total_entities = row[0] if row else 0
            async with self.conn.execute("SELECT COUNT(*) FROM entity_relations") as cursor:
                row = await cursor.fetchone()
                total_rels = row[0] if row else 0

        return {
            "entities": entities,
            "relationships": relationships,
            "stats": {
                "total_entities": total_entities,
                "total_relationships": total_rels
            }
        }

    async def query_entity(self, name: str, project: Optional[str] = None) -> Optional[dict]:
        if not name or not name.strip(): return None
        if project:
            async with self.conn.execute(
                "SELECT id, name, entity_type, project, first_seen, last_seen, mention_count "
                "FROM entities WHERE name = ? AND project = ?",
                (name, project),
            ) as cursor:
                row = await cursor.fetchone()
        else:
            async with self.conn.execute(
                "SELECT id, name, entity_type, project, first_seen, last_seen, mention_count "
                "FROM entities WHERE name = ? ORDER BY mention_count DESC LIMIT 1",
                (name,),
            ) as cursor:
                row = await cursor.fetchone()

        if not row: return None

        entity = {
            "id": row[0], "name": row[1], "type": row[2], "project": row[3],
            "first_seen": row[4], "last_seen": row[5], "mentions": row[6],
        }

        async with self.conn.execute(
            """SELECT e.name, e.entity_type, er.relation_type, er.weight
               FROM entity_relations er
               JOIN entities e ON (
                   CASE WHEN er.source_entity_id = ? THEN er.target_entity_id
                        ELSE er.source_entity_id END = e.id
               )
               WHERE er.source_entity_id = ? OR er.target_entity_id = ?
               ORDER BY er.weight DESC LIMIT 20""",
            (row[0], row[0], row[0]),
        ) as cursor:
            connections = await cursor.fetchall()

        entity["connections"] = [
            {"name": c[0], "type": c[1], "relation": c[2], "weight": c[3]}
            for c in connections
        ]
        return entity

    async def upsert_ghost(self, reference: str, context: str, project: str, timestamp: str) -> int:
        async with self.conn.execute(
            "SELECT id FROM ghosts WHERE reference = ? AND project = ? AND status = 'open'",
            (reference, project),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            return row[0]
        else:
            async with self.conn.execute(
                """INSERT INTO ghosts (reference, context, project, detected_at, status)
                   VALUES (?, ?, ?, ?, 'open')""",
                (reference, context, project, timestamp),
            ) as cursor:
                return cursor.lastrowid

    async def resolve_ghost(self, ghost_id: int | str, target_id: int | str, confidence: float, timestamp: str) -> bool:
        async with self.conn.execute(
            "UPDATE ghosts SET status = 'resolved', resolved_at = ?, target_id = ?, confidence = ? WHERE id = ?",
            (timestamp, target_id, confidence, ghost_id),
        ) as cursor:
            return cursor.rowcount > 0

    async def delete_fact_elements(self, fact_id: int) -> bool:
        async with self.conn.execute(
            "DELETE FROM entity_relations WHERE source_fact_id = ?",
            (fact_id,),
        ) as cursor:
            return cursor.rowcount > 0

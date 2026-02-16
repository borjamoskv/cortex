# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""SQLite Graph Backend."""

import logging
from typing import Optional

import aiosqlite

from .base import GraphBackend

logger = logging.getLogger("cortex.graph.backends")


class SQLiteBackend(GraphBackend):
    def __init__(self, conn):
        self.conn = conn
        # Check if connection is async (aiosqlite)
        self._is_async = isinstance(conn, aiosqlite.Connection)

    async def upsert_entity(self, name: str, entity_type: str, project: str, timestamp: str) -> int:
        query_select = "SELECT id, mention_count FROM entities WHERE name = ? AND project = ?"
        params = (name, project)

        if self._is_async:
            async with self.conn.execute(query_select, params) as cursor:
                row = await cursor.fetchone()
        else:
            row = self.conn.execute(query_select, params).fetchone()

        if row:
            entity_id, count = row
            query_update = "UPDATE entities SET mention_count = ?, last_seen = ? WHERE id = ?"
            if self._is_async:
                await self.conn.execute(query_update, (count + 1, timestamp, entity_id))
            else:
                self.conn.execute(query_update, (count + 1, timestamp, entity_id))
            return entity_id
        else:
            query_insert = """INSERT INTO entities (name, entity_type, project, first_seen, last_seen, mention_count)
                              VALUES (?, ?, ?, ?, ?, 1)"""
            params_insert = (name, entity_type, project, timestamp, timestamp)
            if self._is_async:
                async with self.conn.execute(query_insert, params_insert) as cursor:
                    return cursor.lastrowid
            else:
                cursor = self.conn.execute(query_insert, params_insert)
                return cursor.lastrowid

    def upsert_entity_sync(self, name: str, entity_type: str, project: str, timestamp: str) -> int:
        cursor = self.conn.execute(
            "SELECT id, mention_count FROM entities WHERE name = ? AND project = ?",
            (name, project),
        )
        row = cursor.fetchone()

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

    async def upsert_relationship(
        self, source_id: int, target_id: int, relation_type: str, fact_id: int, timestamp: str
    ) -> int:
        query_select = "SELECT id, weight FROM entity_relations WHERE source_entity_id = ? AND target_entity_id = ?"
        params = (source_id, target_id)

        if self._is_async:
            async with self.conn.execute(query_select, params) as cursor:
                row = await cursor.fetchone()
        else:
            row = self.conn.execute(query_select, params).fetchone()

        if row:
            rel_id, weight = row
            query_update = "UPDATE entity_relations SET weight = ?, relation_type = ? WHERE id = ?"
            if self._is_async:
                await self.conn.execute(query_update, (weight + 0.5, relation_type, rel_id))
            else:
                self.conn.execute(query_update, (weight + 0.5, relation_type, rel_id))
            return rel_id
        else:
            query_insert = """INSERT INTO entity_relations
                               (source_entity_id, target_entity_id, relation_type, weight, first_seen, source_fact_id)
                               VALUES (?, ?, ?, 1.0, ?, ?)"""
            params_insert = (source_id, target_id, relation_type, timestamp, fact_id)
            if self._is_async:
                async with self.conn.execute(query_insert, params_insert) as cursor:
                    return cursor.lastrowid
            else:
                cursor = self.conn.execute(query_insert, params_insert)
                return cursor.lastrowid

    def upsert_relationship_sync(
        self, source_id: int, target_id: int, relation_type: str, fact_id: int, timestamp: str
    ) -> int:
        cursor = self.conn.execute(
            "SELECT id, weight FROM entity_relations WHERE source_entity_id = ? AND target_entity_id = ?",
            (source_id, target_id),
        )
        row = cursor.fetchone()

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

    async def get_graph(self, project: Optional[str] = None, limit: int = 50) -> dict:
        query_entities = "SELECT id, name, entity_type, project, mention_count FROM entities"
        params_entities = []
        if project:
            query_entities += " WHERE project = ?"
            params_entities.append(project)
        query_entities += " ORDER BY mention_count DESC LIMIT ?"
        params_entities.append(limit)

        if self._is_async:
            async with self.conn.execute(query_entities, params_entities) as cursor:
                entity_rows = await cursor.fetchall()
        else:
            entity_rows = self.conn.execute(query_entities, params_entities).fetchall()

        entities = []
        entity_ids = []
        for row in entity_rows:
            entities.append(
                {"id": row[0], "name": row[1], "type": row[2], "project": row[3], "weight": row[4]}
            )
            entity_ids.append(row[0])

        if not entity_ids:
            return {
                "entities": [],
                "relationships": [],
                "stats": {"total_entities": 0, "total_relationships": 0},
            }

        placeholders = ",".join(["?"] * len(entity_ids))
        query_rels = f"""
            SELECT id, source_entity_id, target_entity_id, relation_type, weight
            FROM entity_relations
            WHERE source_entity_id IN ({placeholders}) OR target_entity_id IN ({placeholders})
        """
        params_rels = entity_ids + entity_ids

        if self._is_async:
            async with self.conn.execute(query_rels, params_rels) as cursor:
                rel_rows = await cursor.fetchall()
        else:
            rel_rows = self.conn.execute(query_rels, params_rels).fetchall()

        relationships = []
        for row in rel_rows:
            relationships.append(
                {"id": row[0], "source": row[1], "target": row[2], "type": row[3], "weight": row[4]}
            )

        # Calculate stats
        total_entities = 0
        total_rels = 0
        if project:
            q_ent_count = "SELECT COUNT(*) FROM entities WHERE project = ?"
            q_rel_count = """SELECT COUNT(*) FROM entity_relations er 
                             JOIN entities e ON er.source_entity_id = e.id 
                             WHERE e.project = ?"""
            if self._is_async:
                async with self.conn.execute(q_ent_count, (project,)) as cursor:
                    total_entities = (await cursor.fetchone())[0]
                async with self.conn.execute(q_rel_count, (project,)) as cursor:
                    total_rels = (await cursor.fetchone())[0]
            else:
                total_entities = self.conn.execute(q_ent_count, (project,)).fetchone()[0]
                total_rels = self.conn.execute(q_rel_count, (project,)).fetchone()[0]
        else:
            q_ent_count = "SELECT COUNT(*) FROM entities"
            q_rel_count = "SELECT COUNT(*) FROM entity_relations"
            if self._is_async:
                async with self.conn.execute(q_ent_count) as cursor:
                    total_entities = (await cursor.fetchone())[0]
                async with self.conn.execute(q_rel_count) as cursor:
                    total_rels = (await cursor.fetchone())[0]
            else:
                total_entities = self.conn.execute(q_ent_count).fetchone()[0]
                total_rels = self.conn.execute(q_rel_count).fetchone()[0]

        return {
            "entities": entities,
            "relationships": relationships,
            "stats": {"total_entities": total_entities, "total_relationships": total_rels},
        }

    def get_graph_sync(self, project: Optional[str] = None, limit: int = 50) -> dict:
        if project:
            entity_rows = self.conn.execute(
                "SELECT id, name, entity_type, project, mention_count "
                "FROM entities WHERE project = ? ORDER BY mention_count DESC LIMIT ?",
                (project, limit),
            ).fetchall()
        else:
            entity_rows = self.conn.execute(
                "SELECT id, name, entity_type, project, mention_count "
                "FROM entities ORDER BY mention_count DESC LIMIT ?",
                (limit,),
            ).fetchall()

        entities = []
        entity_ids = []
        for row in entity_rows:
            entities.append(
                {"id": row[0], "name": row[1], "type": row[2], "project": row[3], "weight": row[4]}
            )
            entity_ids.append(row[0])

        if not entity_ids:
            return {
                "entities": [],
                "relationships": [],
                "stats": {"total_entities": 0, "total_relationships": 0},
            }

        placeholders = ",".join(["?"] * len(entity_ids))
        rel_rows = self.conn.execute(
            f"SELECT id, source_entity_id, target_entity_id, relation_type, weight "
            f"FROM entity_relations WHERE source_entity_id IN ({placeholders}) OR target_entity_id IN ({placeholders})",
            entity_ids + entity_ids,
        ).fetchall()

        relationships = []
        for row in rel_rows:
            relationships.append(
                {"id": row[0], "source": row[1], "target": row[2], "type": row[3], "weight": row[4]}
            )

        if project:
            total_entities = self.conn.execute(
                "SELECT COUNT(*) FROM entities WHERE project = ?", (project,)
            ).fetchone()[0]
            total_rels = self.conn.execute(
                "SELECT COUNT(*) FROM entity_relations er JOIN entities e ON er.source_entity_id = e.id WHERE e.project = ?",
                (project,),
            ).fetchone()[0]
        else:
            total_entities = self.conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            total_rels = self.conn.execute("SELECT COUNT(*) FROM entity_relations").fetchone()[0]

        return {
            "entities": entities,
            "relationships": relationships,
            "stats": {"total_entities": total_entities, "total_relationships": total_rels},
        }

    async def query_entity(self, name: str, project: Optional[str] = None) -> Optional[dict]:
        if not name or not name.strip():
            return None

        q_ent = "SELECT id, name, entity_type, project, mention_count FROM entities WHERE name = ?"
        params_ent = [name]
        if project:
            q_ent += " AND project = ?"
            params_ent.append(project)
        else:
            q_ent += " ORDER BY mention_count DESC LIMIT 1"

        if self._is_async:
            async with self.conn.execute(q_ent, params_ent) as cursor:
                row = await cursor.fetchone()
        else:
            row = self.conn.execute(q_ent, params_ent).fetchone()

        if not row:
            return None

        entity = {
            "id": row[0],
            "name": row[1],
            "type": row[2],
            "project": row[3],
            "mentions": row[4],
        }

        q_conn = """SELECT e.name, e.entity_type, er.relation_type, er.weight 
                   FROM entity_relations er 
                   JOIN entities e ON (CASE WHEN er.source_entity_id = ? THEN er.target_entity_id ELSE er.source_entity_id END = e.id)
                   WHERE er.source_entity_id = ? OR er.target_entity_id = ?
                   ORDER BY er.weight DESC LIMIT 20"""

        if self._is_async:
            async with self.conn.execute(q_conn, (row[0], row[0], row[0])) as cursor:
                connections = await cursor.fetchall()
        else:
            connections = self.conn.execute(q_conn, (row[0], row[0], row[0])).fetchall()

        entity["connections"] = [
            {"name": c[0], "type": c[1], "relation": c[2], "weight": c[3]} for c in connections
        ]
        return entity

    def query_entity_sync(self, name: str, project: Optional[str] = None) -> Optional[dict]:
        if not name or not name.strip():
            return None
        q = "SELECT id, name, entity_type, project, mention_count FROM entities WHERE name = ?"
        if project:
            row = self.conn.execute(q + " AND project = ?", (name, project)).fetchone()
        else:
            row = self.conn.execute(q + " ORDER BY mention_count DESC LIMIT 1", (name,)).fetchone()

        if not row:
            return None
        entity = {
            "id": row[0],
            "name": row[1],
            "type": row[2],
            "project": row[3],
            "mentions": row[4],
        }
        connections = self.conn.execute(
            """SELECT e.name, e.entity_type, er.relation_type, er.weight FROM entity_relations er 
               JOIN entities e ON (CASE WHEN er.source_entity_id = ? THEN er.target_entity_id ELSE er.source_entity_id END = e.id)
               WHERE er.source_entity_id = ? OR er.target_entity_id = ? ORDER BY er.weight DESC LIMIT 20""",
            (row[0], row[0], row[0]),
        ).fetchall()
        entity["connections"] = [
            {"name": c[0], "type": c[1], "relation": c[2], "weight": c[3]} for c in connections
        ]
        return entity

    async def find_path(self, source: str, target: str, max_depth: int = 3) -> list[dict]:
        """Find paths between entities using BFS."""
        q_ids = "SELECT id, name FROM entities WHERE name IN (?, ?)"
        if self._is_async:
            async with self.conn.execute(q_ids, (source, target)) as cursor:
                id_map = {row[1]: row[0] for row in await cursor.fetchall()}
        else:
            id_map = {
                row[1]: row[0] for row in self.conn.execute(q_ids, (source, target)).fetchall()
            }

        if source not in id_map or target not in id_map:
            return []

        start_id = id_map[source]
        end_id = id_map[target]
        queue = [(start_id, [])]
        visited = {start_id}

        while queue:
            curr_id, path = queue.pop(0)
            if len(path) >= max_depth:
                continue

            q_neighbors = """SELECT e.id, e.name, er.relation_type, er.weight FROM entity_relations er
                             JOIN entities e ON (CASE WHEN er.source_entity_id = ? THEN er.target_entity_id ELSE er.source_entity_id END = e.id)
                             WHERE er.source_entity_id = ? OR er.target_entity_id = ?"""
            if self._is_async:
                async with self.conn.execute(q_neighbors, (curr_id, curr_id, curr_id)) as cursor:
                    neighbors = await cursor.fetchall()
            else:
                neighbors = self.conn.execute(q_neighbors, (curr_id, curr_id, curr_id)).fetchall()

            for nid, nname, rtype, weight in neighbors:
                new_step = {
                    "source": source if curr_id == start_id else "intermediate",
                    "target": nname,
                    "type": rtype,
                    "weight": weight,
                }
                if nid == end_id:
                    return path + [new_step]
                if nid not in visited:
                    visited.add(nid)
                    queue.append((nid, path + [new_step]))
        return []

    async def find_context_subgraph(
        self, seed_entities: list[str], depth: int = 2, max_nodes: int = 50
    ) -> dict:
        """Retrieve a subgraph around seed entities."""
        if not seed_entities:
            return {"nodes": [], "edges": []}
        nodes = {}
        edges = []
        visited_ids = set()

        placeholders = ",".join(["?"] * len(seed_entities))
        q_init = f"SELECT id, name, entity_type FROM entities WHERE name IN ({placeholders})"
        if self._is_async:
            async with self.conn.execute(q_init, seed_entities) as cursor:
                rows = await cursor.fetchall()
        else:
            rows = self.conn.execute(q_init, seed_entities).fetchall()

        current_layer_ids = []
        for row in rows:
            eid, name, etype = row
            nodes[name] = {"id": eid, "type": etype}
            current_layer_ids.append(eid)
            visited_ids.add(eid)

        for _ in range(depth):
            if not current_layer_ids or len(nodes) >= max_nodes:
                break
            phs = ",".join(["?"] * len(current_layer_ids))
            q_expand = f"""SELECT e1.name, e1.entity_type, e1.id, e2.name, e2.entity_type, e2.id, er.relation_type, er.weight
                          FROM entity_relations er
                          JOIN entities e1 ON er.source_entity_id = e1.id
                          JOIN entities e2 ON er.target_entity_id = e2.id
                          WHERE er.source_entity_id IN ({phs}) OR er.target_entity_id IN ({phs})"""
            params = current_layer_ids + current_layer_ids
            if self._is_async:
                async with self.conn.execute(q_expand, params) as cursor:
                    rel_rows = await cursor.fetchall()
            else:
                rel_rows = self.conn.execute(q_expand, params).fetchall()

            next_layer_ids = []
            for s_name, s_type, s_id, t_name, t_type, t_id, r_type, weight in rel_rows:
                if s_name not in nodes:
                    nodes[s_name] = {"id": s_id, "type": s_type}
                    if s_id not in visited_ids:
                        next_layer_ids.append(s_id)
                        visited_ids.add(s_id)
                if t_name not in nodes:
                    nodes[t_name] = {"id": t_id, "type": t_type}
                    if t_id not in visited_ids:
                        next_layer_ids.append(t_id)
                        visited_ids.add(t_id)
                edge = {"source": s_name, "target": t_name, "type": r_type, "weight": weight}
                if edge not in edges:
                    edges.append(edge)
            current_layer_ids = next_layer_ids
            if len(nodes) >= max_nodes:
                break
        return {"nodes": [{"name": k, **v} for k, v in nodes.items()], "edges": edges}

    async def upsert_ghost(self, reference: str, context: str, project: str, timestamp: str) -> int:
        q_sel = "SELECT id FROM ghosts WHERE reference = ? AND project = ? AND status = 'open'"
        if self._is_async:
            async with self.conn.execute(q_sel, (reference, project)) as cursor:
                row = await cursor.fetchone()
        else:
            row = self.conn.execute(q_sel, (reference, project)).fetchone()
        if row:
            return row[0]
        q_ins = "INSERT INTO ghosts (reference, context, project, detected_at, status) VALUES (?, ?, ?, ?, 'open')"
        if self._is_async:
            async with self.conn.execute(q_ins, (reference, context, project, timestamp)) as cursor:
                return cursor.lastrowid
        else:
            return self.conn.execute(q_ins, (reference, context, project, timestamp)).lastrowid

    async def resolve_ghost(
        self, ghost_id: int, target_id: int, confidence: float, timestamp: str
    ) -> bool:
        q = "UPDATE ghosts SET status = 'resolved', resolved_at = ?, target_id = ?, confidence = ? WHERE id = ?"
        if self._is_async:
            async with self.conn.execute(q, (timestamp, target_id, confidence, ghost_id)) as cursor:
                return cursor.rowcount > 0
        else:
            return self.conn.execute(q, (timestamp, target_id, confidence, ghost_id)).rowcount > 0

    async def delete_fact_elements(self, fact_id: int) -> bool:
        q = "DELETE FROM entity_relations WHERE source_fact_id = ?"
        if self._is_async:
            async with self.conn.execute(q, (fact_id,)) as cursor:
                return cursor.rowcount > 0
        else:
            return self.conn.execute(q, (fact_id,)).rowcount > 0

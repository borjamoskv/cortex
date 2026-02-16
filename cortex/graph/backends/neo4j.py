import logging
import re
from typing import Optional
from cortex.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from .base import GraphBackend

logger = logging.getLogger("cortex.graph.backends")

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

    async def upsert_entity(self, name: str, entity_type: str, project: str, timestamp: str) -> str:
        if not self._initialized: return ""
        
        query = """
        MERGE (e:Entity {name: $name, project: $project})
        ON CREATE SET e.type = $type, e.first_seen = $ts, e.last_seen = $ts, e.mentions = 1
        ON MATCH SET e.last_seen = $ts, e.mentions = e.mentions + 1
        RETURN id(e) as id
        """
        # Note: In a full async production setup, we would use AsyncGraphDatabase
        # For Wave 5, we provide the async interface
        with self.driver.session() as session:
            result = session.run(query, name=name, project=project, type=entity_type, ts=timestamp)
            record = result.single()
            return str(record["id"]) if record else ""

    async def upsert_relationship(self, source_id: int | str, target_id: int | str, relation_type: str, fact_id: int, timestamp: str) -> str:
        if not self._initialized: return ""
        
        rel_type = re.sub(r'\W', '_', relation_type.upper())
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

    async def get_graph(self, project: Optional[str] = None, limit: int = 50) -> dict:
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
        
        return {"entities": entities, "relationships": []}

    async def query_entity(self, name: str, project: Optional[str] = None) -> Optional[dict]:
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
            entity["connections"] = [] 
            return entity

    async def upsert_ghost(self, reference: str, context: str, project: str, timestamp: str) -> str:
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

    async def resolve_ghost(self, ghost_id: int | str, target_id: int | str, confidence: float, timestamp: str) -> bool:
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

    async def delete_fact_elements(self, fact_id: int) -> bool:
        if not self._initialized: return False
        
        query = """
        MATCH ()-[r {fact_id: $fid}]->()
        DELETE r
        RETURN count(r) as deleted
        """
        with self.driver.session() as session:
            result = session.run(query, fid=fact_id)
            record = result.single()
            return record["deleted"] > 0 if record else False

    async def find_path(self, source_name: str, target_name: str, max_depth: int = 3) -> list[dict]:
        if not self._initialized: return []
        
        query = f"""
        MATCH p=shortestPath((s:Entity {{name: $s}})-[*..{max_depth}]-(t:Entity {{name: $t}}))
        RETURN relationships(p) as rels, nodes(p) as nodes
        """
        path_list = []
        with self.driver.session() as session:
            result = session.run(query, s=source_name, t=target_name)
            record = result.single()
            if record:
                rels = record["rels"]
                nodes_in_path = record["nodes"]
                for i, r in enumerate(rels):
                    # Neo4j relationship object
                    path_list.append({
                        "source": nodes_in_path[i]["name"],
                        "target": nodes_in_path[i+1]["name"],
                        "relation": r.type,
                        "weight": r.get("weight", 1.0)
                    })
        return path_list

    async def find_context_subgraph(self, seed_entities: list[str], depth: int = 2, max_nodes: int = 50) -> dict:
        if not self._initialized: return {"entities": [], "relationships": []}

        # Basic CYPHER expansion
        # LIMIT is hard to apply to nodes globally in expansion with plain Cypher without APOC,
        # but we can try a variable length match
        query = f"""
        MATCH (s:Entity) WHERE s.name IN $seeds
        CALL {{
            WITH s
            MATCH (s)-[r*1..{depth}]-(m:Entity)
            RETURN m, r
            LIMIT {max_nodes}
        }}
        RETURN s, m, r
        """
        # Note: The above query is approximate and might return multiple rows per path.
        # A proper subgraph query usually requires APOC or multiple steps.
        # We'll use a simpler expansion for now: get neighbors 
        
        entities_map = {}
        relationships_list = []
        
        with self.driver.session() as session:
            # 1. Get seeds
            result = session.run("MATCH (n:Entity) WHERE n.name IN $seeds RETURN n", seeds=seed_entities)
            for record in result:
                node = record["n"]
                entities_map[node.id] = {
                    "id": node.id, "name": node["name"], "type": node.get("type"), "project": node.get("project")
                }
            
            # 2. Expand (simple 1-hop for now to be safe, or 2-hop loop)
            current_ids = list(entities_map.keys())
            for _ in range(depth):
                if not current_ids: break
                q_expand = f"""
                MATCH (a)-[r]-(b)
                WHERE id(a) IN $ids
                RETURN a, r, b
                LIMIT {max_nodes}
                """
                res = session.run(q_expand, ids=current_ids)
                next_ids = []
                for rec in res:
                    a, r, b = rec["a"], rec["r"], rec["b"]
                    if b.id not in entities_map and len(entities_map) < max_nodes:
                        entities_map[b.id] = {
                            "id": b.id, "name": b["name"], "type": b.get("type"), "project": b.get("project")
                        }
                        next_ids.append(b.id)
                    
                    if a.id in entities_map and b.id in entities_map:
                         relationships_list.append({
                            "source": a["name"],
                            "target": b["name"],
                            "relation": r.type,
                            "weight": r.get("weight", 1.0)
                         })
                current_ids = next_ids

        return {
            "entities": list(entities_map.values()),
            "relationships": relationships_list
        }

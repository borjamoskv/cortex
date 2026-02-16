"""Graph Processing Engine.

Extraction, relationship detection, and backend orchestration.
"""
import logging
from typing import Optional

from cortex.config import GRAPH_BACKEND
from cortex.graph.backends import GraphBackend, Neo4jBackend, SQLiteBackend
from cortex.graph.patterns import COMMON_WORDS, ENTITY_PATTERNS, RELATION_SIGNALS

logger = logging.getLogger("cortex.graph")


def get_backend(conn=None) -> GraphBackend:
    """Get the appropriate graph backend."""
    if GRAPH_BACKEND == "neo4j":
        return Neo4jBackend()
    return SQLiteBackend(conn)  # type: ignore[arg-type]


def extract_entities(content: str) -> list[dict]:
    """Extract entities from text content using regex patterns."""
    if not content or not content.strip():
        return []
    seen: set[str] = set()
    entities: list[dict] = []
    for entity_type, pattern in ENTITY_PATTERNS:
        for match in pattern.finditer(content):
            name = match.group(1).strip()
            name_lower = name.lower()
            if len(name) < 2 or len(name) > 100 or name_lower in seen:
                continue
            if entity_type == "project" and name_lower in COMMON_WORDS:
                continue
            seen.add(name_lower)
            entities.append({"name": name, "entity_type": entity_type})
    return entities


def detect_relationships(content: str, entities: list[dict]) -> list[dict]:
    """Detect relationships between extracted entities via signal matching."""
    if len(entities) < 2:
        return []
    relationships: list[dict] = []
    content_lower = content.lower()
    detected_relation = "related_to"
    for relation_type, signals in RELATION_SIGNALS.items():
        for signal in signals:
            if signal in content_lower:
                detected_relation = relation_type
                break
        if detected_relation != "related_to":
            break
    for i, source in enumerate(entities):
        for target in entities[i + 1:]:
            if source["name"].lower() == target["name"].lower():
                continue
            relationships.append({
                "source_name": source["name"],
                "target_name": target["name"],
                "relation_type": detected_relation,
            })
    return relationships


async def process_fact_graph(
    conn, fact_id: int, content: str, project: str, timestamp: str
) -> tuple[int, int]:
    """Process a fact for graph extraction (async).

    Entity extraction and relationship detection are CPU-bound (regex),
    so they run synchronously. Only the DB writes use await.
    """
    entities = extract_entities(content)
    if not entities:
        return 0, 0
    relationships = detect_relationships(content, entities)

    try:
        entity_ids: dict[str, int] = {}
        for ent in entities:
            cursor = await conn.execute(
                "SELECT id, mention_count FROM entities "
                "WHERE name = ? AND project = ?",
                (ent["name"], project),
            )
            row = await cursor.fetchone()
            if row:
                entity_id, count = row
                await conn.execute(
                    "UPDATE entities SET mention_count = ?, last_seen = ? "
                    "WHERE id = ?",
                    (count + 1, timestamp, entity_id),
                )
            else:
                cursor = await conn.execute(
                    "INSERT INTO entities "
                    "(name, entity_type, project, first_seen, last_seen, mention_count) "
                    "VALUES (?, ?, ?, ?, ?, 1)",
                    (ent["name"], ent["entity_type"], project, timestamp, timestamp),
                )
                entity_id = cursor.lastrowid
            entity_ids[ent["name"]] = entity_id

        for rel in relationships:
            sid = entity_ids.get(rel["source_name"])
            tid = entity_ids.get(rel["target_name"])
            if not sid or not tid:
                continue
            cursor = await conn.execute(
                "SELECT id, weight FROM entity_relations "
                "WHERE source_entity_id = ? AND target_entity_id = ?",
                (sid, tid),
            )
            row = await cursor.fetchone()
            if row:
                rel_id, weight = row
                await conn.execute(
                    "UPDATE entity_relations SET weight = ?, relation_type = ? "
                    "WHERE id = ?",
                    (weight + 0.5, rel["relation_type"], rel_id),
                )
            else:
                await conn.execute(
                    "INSERT INTO entity_relations "
                    "(source_entity_id, target_entity_id, relation_type, "
                    "weight, first_seen, source_fact_id) "
                    "VALUES (?, ?, ?, 1.0, ?, ?)",
                    (sid, tid, rel["relation_type"], timestamp, fact_id),
                )

        # Neo4j dual-write (sync, external service)
        if GRAPH_BACKEND == "neo4j":
            try:
                neo = Neo4jBackend()
                for ent in entities:
                    neo.upsert_entity(
                        ent["name"], ent["entity_type"], project, timestamp
                    )
            except Exception as e:
                logger.warning("Neo4j dual-write failed: %s", e)

        return len(entities), len(relationships)
    except Exception as e:
        logger.warning("Graph processing failed for fact %d: %s", fact_id, e)
        return 0, 0


def process_fact_graph_sync(
    conn, fact_id: int, content: str, project: str, timestamp: str
) -> tuple[int, int]:
    """Process a fact for graph extraction (sync)."""
    entities = extract_entities(content)
    if not entities:
        return 0, 0
    relationships = detect_relationships(content, entities)

    try:
        backend = get_backend(conn)
        entity_ids: dict[str, int] = {}
        for ent in entities:
            eid = backend.upsert_entity_sync(
                ent["name"], ent["entity_type"], project, timestamp
            )
            entity_ids[ent["name"]] = eid

        for rel in relationships:
            source_id = entity_ids.get(rel["source_name"])
            target_id = entity_ids.get(rel["target_name"])
            if source_id and target_id:
                backend.upsert_relationship_sync(
                    source_id, target_id, rel["relation_type"], fact_id, timestamp
                )
        return len(entities), len(relationships)
    except Exception as e:
        logger.warning("Graph processing sync failed for fact %d: %s", fact_id, e)
        return 0, 0




async def get_graph(
    conn, project: Optional[str] = None, limit: int = 50
) -> dict:
    """Get graph data for a project or all projects.

    Args:
        conn: Active database connection.
        project: Optional project filter.
        limit: Maximum entities to return.
    """
    backend = get_backend(conn)
    return await backend.get_graph(project, limit)


def get_graph_sync(
    conn, project: Optional[str] = None, limit: int = 50
) -> dict:
    """Get graph data synchronously."""
    backend = get_backend(conn)
    return backend.get_graph_sync(project, limit)




async def query_entity(
    conn, name: str, project: Optional[str] = None
) -> Optional[dict]:
    """Query a specific entity by name.

    Args:
        conn: Active database connection.
        name: Entity name to search for.
        project: Optional project filter.
    """
    backend = get_backend(conn)
    return await backend.query_entity(name, project)


def query_entity_sync(
    conn, name: str, project: Optional[str] = None
) -> Optional[dict]:
    """Query entity synchronously."""
    backend = get_backend(conn)
    return backend.query_entity_sync(name, project)




async def find_path(
    conn, source: str, target: str, max_depth: int = 3
) -> list[dict]:
    """Find meaningful paths between two entities.

    Useful for explaining connections (e.g., "How is Project A related to Library B?").
    """
    backend = get_backend(conn)
    return await backend.find_path(source, target, max_depth)


async def get_context_subgraph(
    conn, seeds: list[str], depth: int = 2, max_nodes: int = 50
) -> dict:
    """Retrieve a subgraph context for RAG.

    Given a list of seed entities (e.g. from a user query), expand the graph
    to find relevant context.
    """
    backend = get_backend(conn)
    return await backend.find_context_subgraph(seeds, depth, max_nodes)

"""Search mixin module."""
import logging
import sqlite3
from typing import Any

from cortex.graph import extract_entities, get_context_subgraph
from cortex.search import hybrid_search, semantic_search, text_search

logger = logging.getLogger("cortex.engine.search")


class SearchMixin:
    """Mixin for semantic, text, and graph-augmented search operations."""

    async def search(
        self,
        query: str,
        top_k: int = 5,
        project: str | None = None,
        as_of: str | None = None,
        graph_depth: int = 0,
        include_graph: bool = False,
    ) -> list[Any]:
        """Perform hybrid search (Vector + Text) with optional Graph-RAG context."""
        async with self.session() as conn:
            try:
                # 1. Perform Hybrid Search
                embedder = self._get_embedder()
                embedding = embedder.embed(query)
                
                results = await hybrid_search(
                    conn=conn,
                    query=query,
                    query_embedding=embedding,
                    top_k=top_k,
                    project=project,
                    as_of=as_of,
                )
                
                if not results:
                    # Fallback to pure text search if hybrid yields nothing (rare but possible)
                    results = await text_search(conn, query, project, limit=top_k, as_of=as_of)

                # 2. Enrich with Graph Context if requested
                if results and (graph_depth > 0 or include_graph):
                    # Extract entities from query to use as seeds
                    entities = extract_entities(query)
                    seeds = [e["name"] for e in entities]
                    
                    # Also use entities found in the top results content
                    if not seeds and results:
                        top_content = " ".join([r.content for r in results[:2]])
                        top_entities = extract_entities(top_content)
                        seeds = [e["name"] for e in top_entities]

                    if seeds:
                        subgraph = await get_context_subgraph(
                            conn, seeds, depth=graph_depth or 1, max_nodes=50
                        )
                        
                        # Attach graph context to the top result for UI/Agent visibility
                        if results and (subgraph.get("nodes") or subgraph.get("edges")):
                            results[0].context = {
                                "graph": subgraph,
                                "seeds": seeds
                            }

                return results

            except (sqlite3.Error, OSError, RuntimeError) as e:
                logger.exception(f"Hybrid Graph-RAG search failed: {e}")
                # Ultimate fallback to basic text search
                return await text_search(conn, query, project, limit=top_k, as_of=as_of)

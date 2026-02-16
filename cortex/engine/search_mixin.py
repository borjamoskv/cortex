"""Search mixin module."""
import logging
from typing import Any, List, Optional
import aiosqlite
from cortex.search import semantic_search, text_search

logger = logging.getLogger("cortex.engine.search")

class SearchMixin:
    """Mixin for semantic and text search operations."""

    async def search(self, query: str, top_k: int = 5, project: Optional[str] = None, as_of: Optional[str] = None) -> List[Any]:
        # Implementation assumes self.session() and self._get_embedder() exist
        async with self.session() as conn:
            try:
                embedder = self._get_embedder()
                if embedder:
                    embedding = embedder.embed(query)
                    results = await semantic_search(conn, embedding, top_k, project, as_of)
                    if results: return results
            except Exception as e:
                logger.warning(f"Semantic search failed: {e}")
            
            return await text_search(conn, query, project, limit=top_k)

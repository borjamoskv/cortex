"""CORTEX v4.1 — Federated Engine (Tenant Sharding).

Routes operations to per-tenant .db files. Each shard is a full CortexEngine.
A MetaCortex aggregates cross-shard search results via merge-sort on score.

Default mode is 'single' (current behavior). Federation is opt-in via
CORTEX_FEDERATION_MODE=federated.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from cortex.config import FEDERATION_MODE, SHARD_DIR

logger = logging.getLogger("cortex.federation")


class FederatedEngine:
    """Multi-tenant sharded CORTEX with per-tenant SQLite databases.

    Each tenant gets its own isolated .db file under SHARD_DIR.
    Cross-shard search aggregates results and sorts by score.
    """

    def __init__(
        self,
        shard_dir: Path = SHARD_DIR,
        auto_embed: bool = True,
    ):
        self._shard_dir = Path(shard_dir)
        self._shard_dir.mkdir(parents=True, exist_ok=True)
        self._auto_embed = auto_embed
        self._shards: Dict[str, Any] = {}  # tenant_id → CortexEngine
        self._lock = asyncio.Lock()

    async def get_shard(self, tenant_id: str) -> Any:
        """Get or create a CortexEngine for a specific tenant.

        Each shard is lazily initialized on first access.
        """
        # Normalize tenant_id to safe filesystem name
        safe_id = self._sanitize_tenant_id(tenant_id)

        async with self._lock:
            if safe_id in self._shards:
                return self._shards[safe_id]

            from cortex.engine import CortexEngine

            db_path = self._shard_dir / f"{safe_id}.db"
            engine = CortexEngine(db_path=db_path, auto_embed=self._auto_embed)
            await engine.init_db()
            self._shards[safe_id] = engine
            logger.info("Federation: initialized shard for tenant '%s' at %s", tenant_id, db_path)
            return engine

    async def store(
        self,
        tenant_id: str,
        project: str,
        content: str,
        **kwargs,
    ) -> int:
        """Store a fact in the tenant-specific shard."""
        engine = await self.get_shard(tenant_id)
        return await engine.store(project, content, **kwargs)

    async def search(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        top_k: int = 5,
        **kwargs,
    ) -> List:
        """Search across one or all tenant shards.

        If tenant_id is provided, searches only that shard.
        Otherwise, searches all shards and merges results by score.
        """
        if tenant_id:
            engine = await self.get_shard(tenant_id)
            return await engine.search(query, top_k=top_k, **kwargs)

        # Cross-shard search: query all shards in parallel
        async with self._lock:
            shard_items = list(self._shards.items())

        if not shard_items:
            return []

        tasks = [engine.search(query, top_k=top_k, **kwargs) for _, engine in shard_items]
        results_per_shard = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge all results, sorted by score descending
        merged = []
        for results in results_per_shard:
            if isinstance(results, Exception):
                logger.warning("Cross-shard search error: %s", results)
                continue
            merged.extend(results)

        merged.sort(key=lambda r: getattr(r, "score", 0), reverse=True)
        return merged[:top_k]

    async def recall(
        self,
        tenant_id: str,
        project: str,
    ) -> List:
        """Recall facts from a specific tenant shard."""
        engine = await self.get_shard(tenant_id)
        return await engine.recall(project)

    @property
    def shard_count(self) -> int:
        """Number of active tenant shards."""
        return len(self._shards)

    @property
    def tenants(self) -> List[str]:
        """List of active tenant IDs."""
        return list(self._shards.keys())

    async def close_all(self) -> None:
        """Close all tenant shard connections."""
        async with self._lock:
            count = len(self._shards)
            for tenant_id, engine in self._shards.items():
                try:
                    await engine.close()
                except Exception as e:
                    logger.warning("Error closing shard '%s': %s", tenant_id, e)
            self._shards.clear()
        logger.info("Federation: closed all %d shards", count)

    @staticmethod
    def _sanitize_tenant_id(tenant_id: str) -> str:
        """Sanitize tenant_id for safe filesystem usage.

        Only allows alphanumeric, hyphens, and underscores.
        """
        import re

        safe = re.sub(r"[^a-zA-Z0-9_-]", "_", tenant_id.strip())
        if not safe:
            raise ValueError(f"invalid tenant_id: {tenant_id!r}")
        return safe[:128]  # Max 128 chars


def get_engine(auto_embed: bool = True):
    """Factory: returns FederatedEngine or CortexEngine based on config.

    Uses CORTEX_FEDERATION_MODE env var (default: 'single').
    """
    if FEDERATION_MODE == "federated":
        logger.info("Starting in FEDERATED mode (shard_dir=%s)", SHARD_DIR)
        return FederatedEngine(auto_embed=auto_embed)
    else:
        from cortex.engine import CortexEngine

        return CortexEngine(auto_embed=auto_embed)

"""
CORTEX v4.1 — Tenant Router.

Routes requests to the correct database based on tenant_id.
In local mode: single DB for everything.
In Turso mode: one DB per tenant (true isolation).

This is the bridge between auth.py (who the user is) and
storage/ (where their data lives).
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

from cortex.storage import StorageMode, get_storage_mode

logger = logging.getLogger("cortex.storage.router")


class TenantRouter:
    """Routes tenant requests to the correct storage backend.

    Local mode:  All tenants share one SQLite file.
    Turso mode:  Each tenant gets their own cloud database.
    """

    def __init__(self):
        self._mode = get_storage_mode()
        self._connections: dict[str, Any] = {}
        self._base_url = os.environ.get("TURSO_DATABASE_URL", "")
        self._auth_token = os.environ.get("TURSO_AUTH_TOKEN", "")

    async def get_backend(self, tenant_id: str = "default"):
        """Get the storage backend for a specific tenant.

        Args:
            tenant_id: The tenant identifier from auth.

        Returns:
            A StorageBackend instance connected to the tenant's database.
        """
        if self._mode == StorageMode.LOCAL:
            return await self._get_local_backend()

        return await self._get_turso_backend(tenant_id)

    async def _get_local_backend(self):
        """Return the shared local SQLite connection pool."""
        if "local" not in self._connections:
            from cortex.connection_pool import CortexConnectionPool
            from cortex.config import DB_PATH

            pool = CortexConnectionPool(str(DB_PATH))
            await pool.initialize()
            self._connections["local"] = pool
            logger.info("Local storage initialized at %s", DB_PATH)

        return self._connections["local"]

    async def _get_turso_backend(self, tenant_id: str):
        """Get or create a Turso connection for this tenant."""
        if tenant_id in self._connections:
            # Health check existing connection
            conn = self._connections[tenant_id]
            if await conn.health_check():
                return conn
            else:
                logger.warning("Turso connection unhealthy for %s, reconnecting", tenant_id)
                await conn.close()

        from cortex.storage.turso import TursoBackend

        url = TursoBackend.tenant_db_url(self._base_url, tenant_id)
        backend = TursoBackend(url=url, auth_token=self._auth_token)
        await backend.connect()

        self._connections[tenant_id] = backend
        logger.info("Turso backend connected for tenant: %s → %s", tenant_id, url)
        return backend

    async def close_all(self) -> None:
        """Close all tenant connections (for shutdown)."""
        for tenant_id, conn in self._connections.items():
            try:
                await conn.close()
                logger.info("Closed connection for tenant: %s", tenant_id)
            except Exception as e:
                logger.warning("Error closing tenant %s: %s", tenant_id, e)
        self._connections.clear()

    @property
    def mode(self) -> StorageMode:
        return self._mode

    @property
    def active_tenants(self) -> list[str]:
        return list(self._connections.keys())

    def __repr__(self) -> str:
        return (
            f"TenantRouter(mode={self._mode.value}, "
            f"active_tenants={len(self._connections)})"
        )


# ─── Singleton ────────────────────────────────────────────────────────

_router: TenantRouter | None = None


def get_router() -> TenantRouter:
    """Get the global tenant router singleton."""
    global _router
    if _router is None:
        _router = TenantRouter()
    return _router

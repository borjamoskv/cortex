"""
CORTEX v4.1 — Turso (libSQL) Cloud Backend.

Drop-in replacement for local SQLite. Uses libsql-experimental
to connect to Turso cloud databases. Same SQL syntax, global edge.

Environment:
    TURSO_DATABASE_URL=libsql://your-db-name.turso.io
    TURSO_AUTH_TOKEN=your-token-here

Install:
    pip install libsql-experimental
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("cortex.storage.turso")


class TursoBackend:
    """Cloud storage backend using Turso (libSQL).

    Turso is SQLite in the cloud — same syntax, same queries,
    but replicated globally with edge read replicas.

    The API mirrors aiosqlite closely so the engine layer
    doesn't need to know which backend is active.
    """

    def __init__(self, url: str, auth_token: str):
        self.url = url
        self.auth_token = auth_token
        self._conn = None

    async def connect(self) -> None:
        """Establish connection to Turso."""
        try:
            import libsql_experimental as libsql
        except ImportError as exc:
            raise RuntimeError(
                "libsql-experimental not installed. "
                "Run: pip install libsql-experimental"
            ) from exc

        logger.info("Connecting to Turso: %s", self.url)
        self._conn = libsql.connect(
            self.url,
            auth_token=self.auth_token,
        )
        logger.info("Connected to Turso successfully")

    def _ensure_conn(self):
        if self._conn is None:
            raise RuntimeError("TursoBackend not connected. Call connect() first.")

    async def execute(self, sql: str, params: tuple = ()) -> list[dict]:
        """Execute SQL and return rows as list of dicts."""
        self._ensure_conn()
        try:
            cursor = self._conn.execute(sql, params)
            if cursor.description is None:
                return []

            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error("Turso execute error: %s | SQL: %s", e, sql[:200])
            raise

    async def execute_insert(self, sql: str, params: tuple = ()) -> int:
        """Execute INSERT and return lastrowid."""
        self._ensure_conn()
        try:
            cursor = self._conn.execute(sql, params)
            self._conn.commit()
            return cursor.lastrowid or 0
        except Exception as e:
            logger.error("Turso insert error: %s", e)
            raise

    async def executemany(self, sql: str, params_list: list[tuple]) -> None:
        """Execute a statement with multiple parameter sets."""
        self._ensure_conn()
        try:
            for params in params_list:
                self._conn.execute(sql, params)
            self._conn.commit()
        except Exception as e:
            logger.error("Turso executemany error: %s", e)
            raise

    async def executescript(self, script: str) -> None:
        """Execute a multi-statement SQL script.

        libSQL doesn't have executescript, so we split by semicolons
        and execute each statement individually.
        """
        self._ensure_conn()
        statements = [s.strip() for s in script.split(";") if s.strip()]
        try:
            for stmt in statements:
                self._conn.execute(stmt)
            self._conn.commit()
        except Exception as e:
            logger.error("Turso executescript error: %s", e)
            raise

    async def commit(self) -> None:
        """Commit current transaction."""
        self._ensure_conn()
        self._conn.commit()

    async def close(self) -> None:
        """Close the connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception as e:
                logger.warning("Error closing Turso connection: %s", e)
            self._conn = None

    async def health_check(self) -> bool:
        """Check if connection is alive."""
        try:
            result = await self.execute("SELECT 1 AS ok")
            return len(result) > 0 and result[0].get("ok") == 1
        except Exception:
            return False

    # ─── Tenant Management (Turso-specific) ───────────────────────

    @staticmethod
    def tenant_db_url(base_url: str, tenant_id: str) -> str:
        """Generate a per-tenant database URL.

        Turso supports database-per-tenant natively.
        Each tenant gets their own isolated database.

        Example:
            base_url:  "libsql://cortex.turso.io"
            tenant_id: "alice"
            result:    "libsql://cortex-alice.turso.io"
        """
        # Parse the base URL and inject tenant
        if "://" in base_url:
            protocol, rest = base_url.split("://", 1)
            parts = rest.split(".", 1)
            if len(parts) == 2:
                return f"{protocol}://{parts[0]}-{tenant_id}.{parts[1]}"

        # Fallback: just append tenant
        return f"{base_url}-{tenant_id}"

    def __repr__(self) -> str:
        return f"TursoBackend(url={self.url!r}, connected={self._conn is not None})"

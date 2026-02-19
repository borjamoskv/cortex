"""
CORTEX v4.1 — Storage Backend Abstraction.

Pluggable storage layer: switch between local SQLite and Turso (cloud)
via environment variable. The engine layer never knows which backend
is active — it just calls the protocol methods.

Usage:
    CORTEX_STORAGE=local   → SQLite file (default, current behavior)
    CORTEX_STORAGE=turso   → Turso libSQL cloud
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Protocol, runtime_checkable

logger = logging.getLogger("cortex.storage")


class StorageMode(str, Enum):
    LOCAL = "local"
    TURSO = "turso"


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for all storage backends.

    Any backend must implement these methods to be compatible
    with CortexConnectionPool and AsyncCortexEngine.
    """

    async def execute(self, sql: str, params: tuple = ()) -> list[dict]:
        """Execute a single SQL statement and return rows as dicts."""
        ...

    async def execute_insert(self, sql: str, params: tuple = ()) -> int:
        """Execute an INSERT and return the last row ID."""
        ...

    async def executemany(self, sql: str, params_list: list[tuple]) -> None:
        """Execute a statement with multiple parameter sets."""
        ...

    async def executescript(self, script: str) -> None:
        """Execute a multi-statement SQL script."""
        ...

    async def commit(self) -> None:
        """Commit the current transaction."""
        ...

    async def close(self) -> None:
        """Close the connection."""
        ...

    async def health_check(self) -> bool:
        """Return True if the connection is alive."""
        ...


def get_storage_mode() -> StorageMode:
    """Detect storage mode from environment."""
    raw = os.environ.get("CORTEX_STORAGE", "local").lower()
    try:
        return StorageMode(raw)
    except ValueError:
        logger.warning("Unknown CORTEX_STORAGE='%s', falling back to local", raw)
        return StorageMode.LOCAL


def get_storage_config() -> dict:
    """Gather all storage-related config from environment."""
    mode = get_storage_mode()

    config = {"mode": mode}

    if mode == StorageMode.TURSO:
        url = os.environ.get("TURSO_DATABASE_URL", "")
        token = os.environ.get("TURSO_AUTH_TOKEN", "")

        if not url:
            raise ValueError(
                "TURSO_DATABASE_URL is required when CORTEX_STORAGE=turso. "
                "Example: libsql://your-db.turso.io"
            )
        if not token:
            raise ValueError(
                "TURSO_AUTH_TOKEN is required when CORTEX_STORAGE=turso. "
                "Get it from: turso db tokens create <db-name>"
            )

        config["url"] = url
        config["token"] = token

    return config

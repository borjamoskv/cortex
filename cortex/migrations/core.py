"""
CORTEX v4.0 — Schema Migrations Core.
"""

from __future__ import annotations

import logging
import sqlite3

import aiosqlite

from cortex.migrations.registry import MIGRATIONS
from cortex.schema import ALL_SCHEMA

logger = logging.getLogger("cortex")


def ensure_migration_table(conn: sqlite3.Connection):
    """Create the schema_version table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT DEFAULT (datetime('now')),
            description TEXT
        )
    """)
    conn.commit()


def get_current_version(conn: sqlite3.Connection) -> int:
    """Get the current schema version (0 means fresh DB)."""
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return row[0] if row[0] is not None else 0
    except Exception:
        return 0


def run_migrations(conn: sqlite3.Connection) -> int:
    """Run all pending migrations.

    Args:
        conn: SQLite connection.

    Returns:
        Number of migrations applied.
    """
    ensure_migration_table(conn)
    current = get_current_version(conn)

    # Apply base schema if database is fresh (version 0)
    if current == 0:
        logger.info("Fresh database detected. Applying base schema...")
        for stmt in ALL_SCHEMA:
            try:
                conn.executescript(stmt)
            except Exception as e:
                msg = str(e).lower()
                if "vec0" in str(stmt) or "no such module" in msg or "duplicate column" in msg:
                    logger.warning(
                        "Skipping schema statement (likely missing vec0 or exists): %s", e
                    )
                else:
                    raise
        conn.commit()
        logger.info("Base schema applied.")

    applied = 0

    for version, description, func in MIGRATIONS:
        if version > current:
            logger.info("Applying migration %d: %s", version, description)
            try:
                func(conn)
            except (sqlite3.Error, OSError) as e:
                logger.error("Migration %d failed: %s. Skipping.", version, e)
                conn.rollback()
                continue
            conn.execute(
                "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                (version, description),
            )
            conn.commit()
            applied += 1

    if applied:
        logger.info(
            "Applied %d migration(s). Schema now at version %d", applied, get_current_version(conn)
        )
    return applied


async def run_migrations_async(conn: aiosqlite.Connection) -> int:
    """Async version of run_migrations for aiosqlite connections."""
    # Ensure table (sync is fine for one-off but let's be consistent)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT DEFAULT (datetime('now')),
            description TEXT
        )
    """)
    await conn.commit()

    # Get version
    cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
    row = await cursor.fetchone()
    current = row[0] if row and row[0] is not None else 0

    if current == 0:
        logger.info("Fresh database detected. Applying base schema (async)...")
        for stmt in ALL_SCHEMA:
            try:
                await conn.executescript(stmt)
            except Exception as e:
                msg = str(e).lower()
                if "vec0" in str(stmt) or "no such module" in msg or "duplicate column" in msg:
                    logger.warning("Skipping schema statement: %s", e)
                else:
                    raise
        await conn.commit()

    applied = 0
    for version, description, func in MIGRATIONS:
        if version > current:
            logger.info("Applying async migration %d: %s", version, description)
            try:
                # Sync migration functions call conn.execute() / conn.executescript()
                # without await. Run them on aiosqlite's internal worker thread
                # so they use the same thread that owns the connection.
                await conn._execute(func, conn._conn)
            except Exception as e:
                logger.error("Migration %d failed: %s", version, e)
                await conn.rollback()
                continue

            await conn.execute(
                "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                (version, description),
            )
            await conn.commit()
            applied += 1

    return applied

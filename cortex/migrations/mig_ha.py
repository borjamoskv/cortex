"""
CORTEX v4.0 — High Availability Migrations.
"""

import logging
import sqlite3

logger = logging.getLogger("cortex")


def _migration_013_cluster_nodes(conn: sqlite3.Connection):
    """Add tables for HA cluster nodes and vector clocks."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cluster_nodes (
            node_id         TEXT PRIMARY KEY,
            node_name       TEXT NOT NULL,
            node_address    TEXT NOT NULL,
            node_region     TEXT,
            is_active       BOOLEAN DEFAULT 1,
            is_voter        BOOLEAN DEFAULT 1,
            joined_at       TEXT NOT NULL DEFAULT (datetime('now')),
            last_seen_at    TEXT NOT NULL DEFAULT (datetime('now')),
            raft_role       TEXT,
            meta            TEXT DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS vector_clocks (
            node_id         TEXT NOT NULL REFERENCES cluster_nodes(node_id),
            entity_type     TEXT NOT NULL,
            entity_id       TEXT NOT NULL,
            version         INTEGER NOT NULL DEFAULT 0,
            timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (node_id, entity_type, entity_id)
        );

        CREATE TABLE IF NOT EXISTS sync_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id         TEXT NOT NULL,
            sync_type       TEXT NOT NULL,
            entity_type     TEXT NOT NULL,
            entity_count    INTEGER NOT NULL,
            started_at      TEXT NOT NULL,
            completed_at    TEXT,
            status          TEXT,
            details         TEXT
        );
    """)
    logger.info("Migration 013: Created HA cluster tables")

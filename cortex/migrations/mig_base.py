import logging
import sqlite3

logger = logging.getLogger("cortex")


def _migration_001_add_updated_at(conn: sqlite3.Connection):
    """Add updated_at column to facts table if missing."""
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(facts)").fetchall()
    }
    if "updated_at" not in columns:
        conn.execute("ALTER TABLE facts ADD COLUMN updated_at TEXT")
        logger.info("Migration 001: Added 'updated_at' column to facts")


def _migration_002_add_indexes(conn: sqlite3.Connection):
    """Add performance indexes."""
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_facts_project_active "
        "ON facts(project, valid_until)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_facts_type "
        "ON facts(fact_type)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_facts_created "
        "ON facts(created_at DESC)"
    )
    logger.info("Migration 002: Added performance indexes")


def _migration_003_enable_wal(conn: sqlite3.Connection):
    """Enable WAL mode for better concurrent read performance."""
    conn.execute("PRAGMA journal_mode=WAL")
    logger.info("Migration 003: Enabled WAL journal mode")


def _migration_004_vector_index(conn: sqlite3.Connection):
    """Create pruned_embeddings table for embedding lifecycle management.

    NOTE: The original migration attempted ``CREATE INDEX USING ivf0`` which
    is invalid sqlite-vec syntax (vec0 virtual tables do not support secondary
    indexes).  Replaced with a pruning metadata table that stores SHA-256
    hashes of archived embeddings for cold-storage verification.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pruned_embeddings (
            fact_id     INTEGER PRIMARY KEY,
            hash        TEXT NOT NULL,
            dimension   INTEGER NOT NULL DEFAULT 384,
            pruned_at   TEXT NOT NULL DEFAULT (datetime('now')),
            reason      TEXT DEFAULT 'deprecated'
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_pruned_at "
        "ON pruned_embeddings(pruned_at)"
    )
    logger.info("Migration 004: Created pruned_embeddings table (replaces dead IVF index)")


def _migration_005_fts5_setup(conn: sqlite3.Connection):
    """Setup FTS5 virtual table for high-performance text search."""
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5("
        "    content, project, tags, fact_type,"
        "    content='facts', content_rowid='id'"
        ")"
    )
    # Rebuild FTS index from existing facts
    conn.execute("INSERT INTO facts_fts(facts_fts) VALUES('rebuild')")

    # Triggers to keep FTS5 in sync with facts table
    conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
            INSERT INTO facts_fts(rowid, content, project, tags, fact_type)
            VALUES (new.id, new.content, new.project, new.tags, new.fact_type);
        END;

        CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
            INSERT INTO facts_fts(facts_fts, rowid, content, project, tags, fact_type)
            VALUES ('delete', old.id, old.content, old.project, old.tags, old.fact_type);
        END;

        CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
            INSERT INTO facts_fts(facts_fts, rowid, content, project, tags, fact_type)
            VALUES ('delete', old.id, old.content, old.project, old.tags, old.fact_type);
            INSERT INTO facts_fts(rowid, content, project, tags, fact_type)
            VALUES (new.id, new.content, new.project, new.tags, new.fact_type);
        END;
    """)
    logger.info("Migration 005: Initialized FTS5 search table with sync triggers")

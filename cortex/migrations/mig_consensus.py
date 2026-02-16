import logging
import sqlite3

logger = logging.getLogger("cortex")


def _migration_007_consensus_layer(conn: sqlite3.Connection):
    """Implement Neural Swarm Consensus (votes + scores)."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(facts)").fetchall()}
    if "consensus_score" not in columns:
        conn.execute("ALTER TABLE facts ADD COLUMN consensus_score REAL DEFAULT 1.0")
        logger.info("Migration 007: Added 'consensus_score' column to facts")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS consensus_votes (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id INTEGER NOT NULL REFERENCES facts(id),
            agent   TEXT NOT NULL,
            vote    INTEGER NOT NULL, -- 1 (verify), -1 (dispute)
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(fact_id, agent)
        );
        CREATE INDEX IF NOT EXISTS idx_votes_fact ON consensus_votes(fact_id);
    """)
    logger.info("Migration 007: Created 'consensus_votes' table")


def _migration_008_consensus_refinement(conn: sqlite3.Connection):
    """Refine consensus layer: add index and ensure referential integrity."""
    # Index for preventing Sybil lookups and agent vote history
    conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_agent ON consensus_votes(agent)")
    logger.info("Migration 008: Added index on consensus_votes(agent)")


def _migration_009_reputation_consensus(conn: sqlite3.Connection):
    """Implement Reputation-Weighted Consensus (RWC) with agents and v2 votes."""
    # 1. Create tables (using scripts from schema.py)
    # Note: These are 'IF NOT EXISTS' so safe to run even if schema.py were applied
    from cortex.schema import (
        CREATE_AGENTS,
        CREATE_OUTCOMES,
        CREATE_RWC_INDEXES,
        CREATE_TRUST_EDGES,
        CREATE_VOTES_V2,
    )

    conn.executescript(CREATE_AGENTS)
    conn.executescript(CREATE_VOTES_V2)
    conn.executescript(CREATE_TRUST_EDGES)
    conn.executescript(CREATE_OUTCOMES)
    conn.executescript(CREATE_RWC_INDEXES)

    # 2. Migrate existing agents from consensus_votes
    # Use hex(randomblob(16)) for a simple unique ID
    conn.execute("""
        INSERT INTO agents (id, public_key, name, agent_type, reputation_score)
        SELECT 
            lower(hex(randomblob(16))),
            '',
            agent,
            'legacy',
            0.5
        FROM (SELECT DISTINCT agent FROM consensus_votes)
        WHERE agent NOT IN (SELECT name FROM agents);
    """)

    # 3. Migrate existing votes to v2
    conn.execute("""
        INSERT INTO consensus_votes_v2 (
            fact_id, agent_id, vote, vote_weight, 
            agent_rep_at_vote, created_at
        )
        SELECT 
            v.fact_id,
            a.id,
            v.vote,
            0.5, -- Initial weight (rep 0.5 * 1.0)
            0.5,
            v.timestamp
        FROM consensus_votes v
        JOIN agents a ON v.agent = a.name
        WHERE NOT EXISTS (
            SELECT 1 FROM consensus_votes_v2 v2 
            WHERE v2.fact_id = v.fact_id AND v2.agent_id = a.id
        );
    """)
    logger.info("Migration 009: Initialized RWC (agents, votes_v2, outcomes)")

"""
CORTEX v4.0 — SQLite Schema Definitions.

All tables, indexes, and virtual tables for the sovereign memory engine.
"""

SCHEMA_VERSION = "4.0.0"

# ─── Core Facts Table ────────────────────────────────────────────────
CREATE_FACTS = """
CREATE TABLE IF NOT EXISTS facts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT NOT NULL,
    content     TEXT NOT NULL,
    fact_type   TEXT NOT NULL DEFAULT 'knowledge',
    tags        TEXT NOT NULL DEFAULT '[]',
    confidence  TEXT NOT NULL DEFAULT 'stated',
    valid_from  TEXT NOT NULL,
    valid_until TEXT,
    source      TEXT,
    meta        TEXT DEFAULT '{}',
    consensus_score REAL DEFAULT 1.0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    tx_id       INTEGER REFERENCES transactions(id)
);
"""

CREATE_FACTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_facts_project ON facts(project);
CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(fact_type);
CREATE INDEX IF NOT EXISTS idx_facts_proj_type ON facts(project, fact_type);
CREATE INDEX IF NOT EXISTS idx_facts_valid ON facts(valid_from, valid_until);
CREATE INDEX IF NOT EXISTS idx_facts_confidence ON facts(confidence);
"""

# ─── Vector Embeddings (sqlite-vec) ──────────────────────────────────
CREATE_EMBEDDINGS = """
CREATE VIRTUAL TABLE IF NOT EXISTS fact_embeddings USING vec0(
    fact_id INTEGER PRIMARY KEY,
    embedding FLOAT[384]
);
"""

# ─── Sessions Log ────────────────────────────────────────────────────
CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    date            TEXT NOT NULL,
    focus           TEXT NOT NULL DEFAULT '[]',
    summary         TEXT NOT NULL,
    conversations   INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# ─── Transaction Ledger (append-only, hash-chained) ──────────────────
CREATE_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT NOT NULL,
    action      TEXT NOT NULL,
    detail      TEXT,
    prev_hash   TEXT,
    hash        TEXT NOT NULL,
    timestamp   TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_TRANSACTIONS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_tx_project ON transactions(project);
CREATE INDEX IF NOT EXISTS idx_tx_action ON transactions(action);
"""

# ─── Heartbeats (activity pulses for time tracking) ──────────────────
CREATE_HEARTBEATS = """
CREATE TABLE IF NOT EXISTS heartbeats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT NOT NULL,
    entity      TEXT,
    category    TEXT NOT NULL,
    branch      TEXT,
    language    TEXT,
    timestamp   TEXT NOT NULL,
    meta        TEXT DEFAULT '{}'
);
"""

CREATE_HEARTBEATS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_hb_project ON heartbeats(project);
CREATE INDEX IF NOT EXISTS idx_hb_timestamp ON heartbeats(timestamp);
CREATE INDEX IF NOT EXISTS idx_hb_category ON heartbeats(category);
"""

# ─── Time Entries (grouped heartbeat blocks) ─────────────────────────
CREATE_TIME_ENTRIES = """
CREATE TABLE IF NOT EXISTS time_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT NOT NULL,
    category    TEXT NOT NULL,
    start_time  TEXT NOT NULL,
    end_time    TEXT NOT NULL,
    duration_s  INTEGER NOT NULL,
    entities    TEXT DEFAULT '[]',
    heartbeats  INTEGER DEFAULT 0,
    meta        TEXT DEFAULT '{}'
);
"""

CREATE_TIME_ENTRIES_INDEX = """
CREATE INDEX IF NOT EXISTS idx_te_project ON time_entries(project);
CREATE INDEX IF NOT EXISTS idx_te_start ON time_entries(start_time);
"""

# ─── Metadata Table ──────────────────────────────────────────────────
CREATE_META = """
CREATE TABLE IF NOT EXISTS cortex_meta (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);
"""

# ─── Consensus Votes (Neural Swarm Consensus) ───────────────────────
CREATE_VOTES = """
CREATE TABLE IF NOT EXISTS consensus_votes (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id INTEGER NOT NULL REFERENCES facts(id),
    agent   TEXT NOT NULL,
    vote    INTEGER NOT NULL, -- 1 (verify), -1 (dispute)
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(fact_id, agent)
);
"""

# ─── Reputation-Weighted Consensus (v2) ─────────────────────────────
CREATE_AGENTS = """
CREATE TABLE IF NOT EXISTS agents (
    id              TEXT PRIMARY KEY,
    public_key      TEXT NOT NULL,
    name            TEXT NOT NULL,
    agent_type      TEXT NOT NULL DEFAULT 'ai',
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    reputation_score    REAL NOT NULL DEFAULT 0.5,
    reputation_stake    REAL NOT NULL DEFAULT 0.0,
    total_votes         INTEGER DEFAULT 0,
    successful_votes    INTEGER DEFAULT 0,
    disputed_votes      INTEGER DEFAULT 0,
    last_active_at      TEXT NOT NULL DEFAULT (datetime('now')),
    is_active           BOOLEAN DEFAULT TRUE,
    is_verified         BOOLEAN DEFAULT FALSE,
    meta                TEXT DEFAULT '{}'
);
"""

CREATE_VOTES_V2 = """
CREATE TABLE IF NOT EXISTS consensus_votes_v2 (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id         INTEGER NOT NULL REFERENCES facts(id),
    agent_id        TEXT NOT NULL REFERENCES agents(id),
    vote            INTEGER NOT NULL,
    vote_weight     REAL NOT NULL,
    agent_rep_at_vote   REAL NOT NULL,
    stake_at_vote       REAL DEFAULT 0.0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    decay_factor    REAL DEFAULT 1.0,
    vote_reason     TEXT,
    meta            TEXT DEFAULT '{}',
    UNIQUE(fact_id, agent_id)
);
"""

CREATE_TRUST_EDGES = """
CREATE TABLE IF NOT EXISTS trust_edges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_agent    TEXT NOT NULL REFERENCES agents(id),
    target_agent    TEXT NOT NULL REFERENCES agents(id),
    trust_weight    REAL NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source_agent, target_agent)
);
"""

CREATE_OUTCOMES = """
CREATE TABLE IF NOT EXISTS consensus_outcomes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id         INTEGER NOT NULL REFERENCES facts(id),
    final_state     TEXT NOT NULL,
    final_score     REAL NOT NULL,
    resolved_at     TEXT NOT NULL DEFAULT (datetime('now')),
    total_votes     INTEGER NOT NULL,
    unique_agents   INTEGER NOT NULL,
    reputation_sum  REAL NOT NULL,
    resolution_method   TEXT DEFAULT 'reputation_weighted',
    meta                TEXT DEFAULT '{}'
);
"""

CREATE_RWC_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_agents_reputation ON agents(reputation_score DESC);
CREATE INDEX IF NOT EXISTS idx_agents_active ON agents(is_active, last_active_at);
CREATE INDEX IF NOT EXISTS idx_votes_v2_fact ON consensus_votes_v2(fact_id);
CREATE INDEX IF NOT EXISTS idx_votes_v2_agent ON consensus_votes_v2(agent_id);
CREATE INDEX IF NOT EXISTS idx_trust_source ON trust_edges(source_agent);
CREATE INDEX IF NOT EXISTS idx_trust_target ON trust_edges(target_agent);
"""

# ─── Ghosts (Unresolved Entities) ────────────────────────────────────
CREATE_GHOSTS = """
CREATE TABLE IF NOT EXISTS ghosts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    reference       TEXT NOT NULL,
    context         TEXT,
    project         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'open', -- open, resolved
    target_id       INTEGER,
    confidence      REAL DEFAULT 0.0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at     TEXT,
    meta            TEXT DEFAULT '{}'
);
"""

CREATE_GHOSTS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_ghosts_ref ON ghosts(reference);
"""

# ─── Graph CDC Outbox (Consistency) ──────────────────────────────────
CREATE_GRAPH_OUTBOX = """
CREATE TABLE IF NOT EXISTS graph_outbox (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id     INTEGER NOT NULL,
    action      TEXT NOT NULL, -- e.g. 'deprecate'
    payload     TEXT,
    status      TEXT NOT NULL DEFAULT 'pending', -- pending, processed, failed
    retry_count INTEGER DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    processed_at TEXT
);
"""

CREATE_GRAPH_OUTBOX_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_graph_outbox_status ON graph_outbox(status);
CREATE INDEX IF NOT EXISTS idx_graph_outbox_fact ON graph_outbox(fact_id);
"""

# ─── All statements in order ─────────────────────────────────────────
ALL_SCHEMA = [
    CREATE_FACTS,
    CREATE_FACTS_INDEXES,
    CREATE_EMBEDDINGS,
    CREATE_SESSIONS,
    CREATE_TRANSACTIONS,
    CREATE_TRANSACTIONS_INDEX,
    CREATE_HEARTBEATS,
    CREATE_HEARTBEATS_INDEX,
    CREATE_TIME_ENTRIES,
    CREATE_TIME_ENTRIES_INDEX,
    CREATE_META,
    CREATE_VOTES,
    CREATE_AGENTS,
    CREATE_VOTES_V2,
    CREATE_TRUST_EDGES,
    CREATE_OUTCOMES,
    CREATE_RWC_INDEXES,
    CREATE_GHOSTS,
    CREATE_GHOSTS_INDEX,
    CREATE_GRAPH_OUTBOX,
    CREATE_GRAPH_OUTBOX_INDEXES,
]


def get_init_meta() -> list[tuple[str, str]]:
    """Return initial metadata key-value pairs."""
    return [
        ("schema_version", SCHEMA_VERSION),
        ("engine", "cortex"),
        ("created_by", "cortex-init"),
    ]

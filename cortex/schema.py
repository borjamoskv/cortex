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
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_FACTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_facts_project ON facts(project);
CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(fact_type);
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
]


def get_init_meta() -> list[tuple[str, str]]:
    """Return initial metadata key-value pairs."""
    return [
        ("schema_version", SCHEMA_VERSION),
        ("engine", "cortex"),
        ("created_by", "cortex-init"),
    ]

""" CORTEX Engine — Package init. """
from __future__ import annotations
import hashlib
import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional
import sqlite_vec
from cortex.embeddings import LocalEmbedder
from cortex.schema import get_init_meta
from cortex.migrations import run_migrations
from cortex.graph import get_graph
from cortex.temporal import now_iso
from cortex.config import DEFAULT_DB_PATH
from cortex.engine.models import Fact, row_to_fact
from cortex.engine.store_mixin import StoreMixin
from cortex.engine.query_mixin import QueryMixin
from cortex.engine.consensus_mixin import ConsensusMixin

logger = logging.getLogger("cortex")

class CortexEngine(StoreMixin, QueryMixin, ConsensusMixin):
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH, auto_embed: bool = True):
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._auto_embed = auto_embed
        self._embedder = None; self._conn = None; self._vec_available = False

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn: return self._conn
        self._conn = sqlite3.connect(str(self._db_path), timeout=30, check_same_thread=False)
        try:
            if hasattr(self._conn, 'enable_load_extension'): self._conn.enable_load_extension(True)
            sqlite_vec.load(self._conn)
            if hasattr(self._conn, 'enable_load_extension'): self._conn.enable_load_extension(False)
            self._vec_available = True
        except: self._vec_available = False
        self._conn.execute("PRAGMA journal_mode=WAL"); self._conn.execute("PRAGMA synchronous=NORMAL"); self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _get_embedder(self):
        if not self._embedder: self._embedder = LocalEmbedder()
        return self._embedder

    def init_db(self):
        from cortex.schema import ALL_SCHEMA
        conn = self._get_conn()
        for stmt in ALL_SCHEMA:
            if "USING vec0" in stmt and not self._vec_available: continue
            conn.executescript(stmt)
        conn.commit(); run_migrations(conn)
        for k, v in get_init_meta(): conn.execute("INSERT OR IGNORE INTO cortex_meta (key, value) VALUES (?, ?)", (k, v))
        conn.commit()

    def _log_transaction(self, conn, project, action, detail) -> int:
        dj = json.dumps(detail, default=str); ts = now_iso()
        prev = conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1").fetchone()
        ph = prev[0] if prev else "GENESIS"
        th = hashlib.sha256(f"{ph}:{project}:{action}:{dj}:{ts}".encode()).hexdigest()
        c = conn.execute("INSERT INTO transactions (project, action, detail, prev_hash, hash, timestamp) VALUES (?, ?, ?, ?, ?, ?)", (project, action, dj, ph, th, ts))
        return c.lastrowid

    def _row_to_fact(self, row) -> Fact: return row_to_fact(row)
    def close(self):
        if self._conn: self._conn.close(); self._conn = None
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

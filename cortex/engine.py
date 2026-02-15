"""
CORTEX v4.0 — Core Engine.

The sovereign memory engine. Manages facts, embeddings, temporal queries,
and the transaction ledger. Single SQLite database, zero network deps.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import sqlite_vec

from cortex.embeddings import LocalEmbedder
from cortex.schema import ALL_SCHEMA, get_init_meta
from cortex.search import SearchResult, semantic_search, text_search
from cortex.temporal import build_temporal_filter_params, now_iso

logger = logging.getLogger("cortex")

DEFAULT_DB_PATH = Path.home() / ".cortex" / "cortex.db"


@dataclass
class Fact:
    """A single fact stored in CORTEX."""

    id: int
    project: str
    content: str
    fact_type: str
    tags: list[str]
    confidence: str
    valid_from: str
    valid_until: Optional[str]
    source: Optional[str]
    meta: dict

    def is_active(self) -> bool:
        return self.valid_until is None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project": self.project,
            "content": self.content,
            "type": self.fact_type,
            "tags": self.tags,
            "confidence": self.confidence,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "source": self.source,
            "active": self.is_active(),
        }


class CortexEngine:
    """The Sovereign Ledger for AI Agents.

    Core engine providing:
    - Semantic vector search (sqlite-vec)
    - Temporal fact management (valid_from/valid_until)
    - Project-scoped isolation
    - Append-only transaction ledger

    Usage:
        engine = CortexEngine()
        engine.store("naroa-web", "Uses vanilla JS, no framework")
        results = engine.search("what framework does naroa use?")
    """

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        auto_embed: bool = True,
    ):
        """Initialize or open CORTEX database.

        Args:
            db_path: Path to SQLite database file.
            auto_embed: Whether to auto-generate embeddings on store.
        """
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._auto_embed = auto_embed
        self._embedder: Optional[LocalEmbedder] = None
        self._conn: Optional[sqlite3.Connection] = None
        self._vec_available = False

    # ─── Connection Management ────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create SQLite connection with vec0 extension."""
        if self._conn is not None:
            return self._conn

        self._conn = sqlite3.connect(
            str(self._db_path), timeout=10, check_same_thread=False
        )

        # Load sqlite-vec extension — handles both standard and restricted builds
        try:
            if hasattr(self._conn, 'enable_load_extension'):
                self._conn.enable_load_extension(True)
            sqlite_vec.load(self._conn)
            if hasattr(self._conn, 'enable_load_extension'):
                self._conn.enable_load_extension(False)
            self._vec_available = True
        except Exception as e:
            logger.warning(f"sqlite-vec not available: {e}. Vector search disabled.")
            self._vec_available = False

        # Performance pragmas
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        return self._conn

    def _get_embedder(self) -> LocalEmbedder:
        """Get or create local embedder (lazy load)."""
        if self._embedder is None:
            self._embedder = LocalEmbedder()
        return self._embedder

    # ─── Database Initialization ──────────────────────────────────

    def init_db(self) -> None:
        """Initialize database schema. Safe to call multiple times."""
        conn = self._get_conn()
        for statement in ALL_SCHEMA:
            # Skip vec0 virtual table if extension not available
            if "vec0" in statement and not self._vec_available:
                logger.info("Skipping vec0 table (extension not available)")
                continue
            for sql in statement.strip().split(";"):
                sql = sql.strip()
                if sql:
                    conn.execute(sql)

        # Insert metadata if not exists
        for key, value in get_init_meta():
            conn.execute(
                "INSERT OR IGNORE INTO cortex_meta (key, value) VALUES (?, ?)",
                (key, value),
            )

        conn.commit()
        logger.info(f"CORTEX database initialized at {self._db_path}")

    # ─── Store ────────────────────────────────────────────────────

    def store(
        self,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: Optional[list[str]] = None,
        confidence: str = "stated",
        source: Optional[str] = None,
        meta: Optional[dict] = None,
        valid_from: Optional[str] = None,
    ) -> int:
        """Store a fact with automatic embedding and temporal metadata.

        Args:
            project: Project/tenant scope.
            content: The fact content.
            fact_type: Type (knowledge, decision, error, bridge, ghost).
            tags: Optional list of tags.
            confidence: Confidence level (stated, verified, hypothesis, deprecated).
            source: Where the fact came from.
            meta: Additional metadata dict.
            valid_from: When fact became valid (default: now).

        Returns:
            The fact ID.
        """
        conn = self._get_conn()
        ts = valid_from or now_iso()
        tags_json = json.dumps(tags or [])
        meta_json = json.dumps(meta or {})

        cursor = conn.execute(
            """
            INSERT INTO facts (project, content, fact_type, tags, confidence,
                              valid_from, source, meta, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (project, content, fact_type, tags_json, confidence,
             ts, source, meta_json, ts, ts),
        )
        fact_id = cursor.lastrowid

        # Auto-embed (only if vec0 available)
        if self._auto_embed and self._vec_available:
            try:
                embedder = self._get_embedder()
                embedding = embedder.embed(content)
                embedding_json = json.dumps(embedding)
                conn.execute(
                    "INSERT INTO fact_embeddings (fact_id, embedding) VALUES (?, ?)",
                    (fact_id, embedding_json),
                )
            except Exception as e:
                logger.warning(f"Embedding failed for fact {fact_id}: {e}")

        # Log transaction
        self._log_transaction(conn, project, "store", {
            "fact_id": fact_id,
            "fact_type": fact_type,
            "content_preview": content[:100],
        })

        conn.commit()
        logger.info(f"Stored fact #{fact_id} in project '{project}'")
        return fact_id

    # ─── Search ───────────────────────────────────────────────────

    def search(
        self,
        query: str,
        project: Optional[str] = None,
        top_k: int = 5,
        as_of: Optional[str] = None,
    ) -> list[SearchResult]:
        """Semantic search across facts.

        Args:
            query: Natural language query.
            project: Optional project scope.
            top_k: Number of results.
            as_of: Optional temporal filter (ISO 8601).

        Returns:
            List of SearchResult ordered by relevance.
        """
        conn = self._get_conn()

        temporal_clause = None
        if as_of:
            clause, _ = build_temporal_filter_params(as_of)
            temporal_clause = clause

        # Try semantic search first
        try:
            embedder = self._get_embedder()
            query_embedding = embedder.embed(query)
            results = semantic_search(
                conn, query_embedding, top_k, project, temporal_clause
            )
            if results:
                return results
        except Exception as e:
            logger.warning(f"Semantic search failed, falling back to text: {e}")

        # Fallback to text search
        return text_search(conn, query, project, limit=top_k)

    # ─── Recall (Project Context) ─────────────────────────────────

    def recall(self, project: str) -> list[Fact]:
        """Load all active facts for a project.

        Args:
            project: Project identifier.

        Returns:
            List of active Facts for the project.
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """
            SELECT id, project, content, fact_type, tags, confidence,
                   valid_from, valid_until, source, meta
            FROM facts
            WHERE project = ? AND valid_until IS NULL
            ORDER BY fact_type, created_at DESC
            """,
            (project,),
        )

        return [self._row_to_fact(row) for row in cursor.fetchall()]

    # ─── History (Temporal Query) ─────────────────────────────────

    def history(
        self,
        project: str,
        as_of: Optional[str] = None,
    ) -> list[Fact]:
        """Get facts as they were at a specific point in time.

        Args:
            project: Project identifier.
            as_of: ISO 8601 timestamp. None = all facts ever.

        Returns:
            List of Facts valid at the given time.
        """
        conn = self._get_conn()

        if as_of:
            clause, params = build_temporal_filter_params(as_of)
            cursor = conn.execute(
                f"""
                SELECT id, project, content, fact_type, tags, confidence,
                       valid_from, valid_until, source, meta
                FROM facts
                WHERE project = ? AND {clause}
                ORDER BY valid_from DESC
                """,
                [project] + params,
            )
        else:
            cursor = conn.execute(
                """
                SELECT id, project, content, fact_type, tags, confidence,
                       valid_from, valid_until, source, meta
                FROM facts
                WHERE project = ?
                ORDER BY valid_from DESC
                """,
                (project,),
            )

        return [self._row_to_fact(row) for row in cursor.fetchall()]

    # ─── Deprecate ────────────────────────────────────────────────

    def deprecate(self, fact_id: int, reason: Optional[str] = None) -> bool:
        """Mark a fact as no longer valid. Never deletes.

        Args:
            fact_id: The fact to deprecate.
            reason: Optional reason for deprecation.

        Returns:
            True if fact was found and deprecated.
        """
        conn = self._get_conn()
        ts = now_iso()

        result = conn.execute(
            """
            UPDATE facts
            SET valid_until = ?, updated_at = ?,
                meta = json_set(COALESCE(meta, '{}'), '$.deprecation_reason', ?)
            WHERE id = ? AND valid_until IS NULL
            """,
            (ts, ts, reason or "deprecated", fact_id),
        )

        if result.rowcount > 0:
            # Fetch project for transaction log
            row = conn.execute("SELECT project FROM facts WHERE id = ?", (fact_id,)).fetchone()
            project = row[0] if row else "__unknown__"

            self._log_transaction(conn, project, "deprecate", {
                "fact_id": fact_id,
                "reason": reason,
            })
            conn.commit()
            logger.info(f"Deprecated fact #{fact_id}")
            return True

        return False

    # ─── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Get database statistics."""
        conn = self._get_conn()

        total = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE valid_until IS NULL"
        ).fetchone()[0]
        deprecated = total - active

        projects = conn.execute(
            "SELECT DISTINCT project FROM facts WHERE valid_until IS NULL"
        ).fetchall()
        project_list = [p[0] for p in projects]

        types = conn.execute(
            """
            SELECT fact_type, COUNT(*) FROM facts
            WHERE valid_until IS NULL
            GROUP BY fact_type
            """
        ).fetchall()

        if self._vec_available:
            embeddings = conn.execute(
                "SELECT COUNT(*) FROM fact_embeddings"
            ).fetchone()[0]
        else:
            embeddings = 0

        transactions = conn.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0]

        return {
            "total_facts": total,
            "active_facts": active,
            "deprecated_facts": deprecated,
            "projects": project_list,
            "project_count": len(project_list),
            "types": {t: c for t, c in types},
            "embeddings": embeddings,
            "transactions": transactions,
            "db_path": str(self._db_path),
            "db_size_mb": round(self._db_path.stat().st_size / 1_048_576, 2)
            if self._db_path.exists() else 0,
        }

    # ─── Transaction Ledger ───────────────────────────────────────

    def _log_transaction(
        self,
        conn: sqlite3.Connection,
        project: str,
        action: str,
        detail: dict,
    ) -> None:
        """Log an action to the immutable transaction ledger."""
        detail_json = json.dumps(detail, default=str)
        ts = now_iso()

        # Get previous hash for chain
        prev = conn.execute(
            "SELECT hash FROM transactions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        prev_hash = prev[0] if prev else "GENESIS"

        # Compute hash: SHA-256(prev_hash + project + action + detail + timestamp)
        hash_input = f"{prev_hash}:{project}:{action}:{detail_json}:{ts}"
        tx_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        conn.execute(
            """
            INSERT INTO transactions (project, action, detail, prev_hash, hash, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (project, action, detail_json, prev_hash, tx_hash, ts),
        )

    # ─── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _row_to_fact(row: tuple) -> Fact:
        """Convert a database row to a Fact object."""
        return Fact(
            id=row[0],
            project=row[1],
            content=row[2],
            fact_type=row[3],
            tags=json.loads(row[4]) if row[4] else [],
            confidence=row[5],
            valid_from=row[6],
            valid_until=row[7],
            source=row[8],
            meta=json.loads(row[9]) if row[9] else {},
        )

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __repr__(self) -> str:
        return f"CortexEngine(db='{self._db_path}')"

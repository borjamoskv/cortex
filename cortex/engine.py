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
from cortex.exceptions import DatabaseTransactionError
from cortex.schema import get_init_meta
from cortex.migrations import run_migrations
from cortex.search import SearchResult, semantic_search, text_search
from cortex.graph import get_graph # query_entity moved to method to break circularity
from cortex.temporal import build_temporal_filter_params, now_iso

logger = logging.getLogger("cortex")

from cortex.config import DEFAULT_DB_PATH


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
    created_at: str
    updated_at: str
    consensus_score: float = 1.0
    tx_id: Optional[int] = None
    hash: Optional[str] = None

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
            "consensus_score": self.consensus_score,
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
            str(self._db_path), timeout=30, check_same_thread=False
        )

        # Load sqlite-vec extension — handles both standard and restricted builds
        try:
            if hasattr(self._conn, 'enable_load_extension'):
                self._conn.enable_load_extension(True)
            sqlite_vec.load(self._conn)
            if hasattr(self._conn, 'enable_load_extension'):
                self._conn.enable_load_extension(False)
            self._vec_available = True
        except (OSError, AttributeError) as e:
            logger.warning("sqlite-vec not available: %s. Vector search disabled.", e)
            self._vec_available = False

        # Performance pragmas
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        return self._conn

    def get_connection(self) -> sqlite3.Connection:
        """Public alias for _get_conn (backward compatibility)."""
        return self._get_conn()

    def _get_embedder(self) -> LocalEmbedder:
        """Get or create local embedder (lazy load)."""
        if self._embedder is None:
            self._embedder = LocalEmbedder()
        return self._embedder

    # ─── Database Initialization ──────────────────────────────────

    def init_db(self) -> None:
        """Initialize database schema using migrations. Safe to call multiple times."""
        from cortex.schema import ALL_SCHEMA, get_init_meta
        conn = self._get_conn()
        
        # 1. Initialize base schema if not existing
        for stmt in ALL_SCHEMA:
            # Skip vector tables if extension is not loaded
            if "USING vec0" in stmt and not self._vec_available:
                continue
            conn.executescript(stmt)
        conn.commit()
        
        # 2. Run migrations (creates/updates tables)
        run_migrations(conn)

        # 3. Insert metadata if not exists
        for key, value in get_init_meta():
            conn.execute(
                "INSERT OR IGNORE INTO cortex_meta (key, value) VALUES (?, ?)",
                (key, value),
            )

        conn.commit()
        logger.info("CORTEX database initialized (schema + migrated) at %s", self._db_path)

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
        commit: bool = True,
        tx_id: Optional[int] = None,
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
            commit: Whether to commit the transaction (False for batch ops).
            tx_id: Optional transaction ID to link to.

        Returns:
            The fact ID.
        """
        if not project or not project.strip():
            raise ValueError("project cannot be empty")
        if not content or not content.strip():
            raise ValueError("content cannot be empty")

        conn = self._get_conn()
        ts = valid_from or now_iso()
        tags_json = json.dumps(tags or [])
        meta_json = json.dumps(meta or {})

        cursor = conn.execute(
            """
            INSERT INTO facts (project, content, fact_type, tags, confidence,
                              valid_from, source, meta, created_at, updated_at, tx_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (project, content, fact_type, tags_json, confidence,
             ts, source, meta_json, ts, ts, tx_id),
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
            except (ValueError, sqlite3.Error) as e:
                logger.warning("Embedding failed for fact %d: %s", fact_id, e)
        
        # Auto-extract Graph Entities & Relationships
        from cortex.graph import process_fact_graph
        try:
            process_fact_graph(conn, fact_id, content, project, ts)
        except Exception as e:
            logger.warning("Graph extraction failed for fact %d: %s", fact_id, e)

        # Log transaction
        tx_id = self._log_transaction(conn, project, "store", {
            "fact_id": fact_id,
            "fact_type": fact_type,
            "content_preview": content[:100],
        })
        
        # Link fact to this transaction (Atomic)
        conn.execute("UPDATE facts SET tx_id = ? WHERE id = ?", (tx_id, fact_id))

        if commit:
            conn.commit()
            logger.info("Stored fact #%d in project '%s'", fact_id, project)
        return fact_id

    def store_many(self, facts: list[dict]) -> list[int]:
        """Store multiple facts atomically. Full ROLLBACK on any failure.

        If any single record fails, the entire batch is reverted.
        Validation errors (ValueError) pass through unchanged.
        Database errors are wrapped in DatabaseTransactionError to avoid
        leaking internal SQLite details.
        """
        if not facts:
            raise ValueError("Cannot store empty list of facts")

        conn = self._get_conn()
        ids = []
        try:
            with conn:  # BEGIN/COMMIT/ROLLBACK managed by context manager
                for f in facts:
                    if "project" not in f or not f["project"] or not str(f["project"]).strip():
                        raise ValueError("Fact must have project")
                    if "content" not in f or not f["content"] or not str(f["content"]).strip():
                        raise ValueError("Fact must have content")

                    fid = self.store(
                        project=f["project"],
                        content=f["content"],
                        fact_type=f.get("fact_type", "knowledge"),
                        tags=f.get("tags", []),
                        confidence=f.get("confidence", "stated"),
                        source=f.get("source", None),
                        meta=f.get("meta", None),
                        valid_from=f.get("valid_from", None),
                        commit=False,
                    )
                    ids.append(fid)
            logger.info("Batch stored %d facts", len(ids))
            return ids
        except sqlite3.Error as e:
            # Rollback already executed by context manager
            logger.error(
                "Batch insert failed. Transaction rolled back safely. Error: %s", e
            )
            raise DatabaseTransactionError(
                "Error crítico al persistir los datos. Cambios revertidos."
            ) from e
        except ValueError:
            # Validation errors pass through unchanged
            raise

    def update(
        self,
        fact_id: int,
        content: Optional[str] = None,
        tags: Optional[list[str]] = None,
        meta: Optional[dict] = None,
    ) -> int:
        """Update a fact by deprecating the old one and creating a new one.

        Args:
            fact_id: ID of the fact to update.
            content: New content (optional).
            tags: New tags (optional).
            meta: New metadata (optional).

        Returns:
            The ID of the new fact.
        """
        if fact_id <= 0:
            raise ValueError("Invalid fact ID")

        conn = self._get_conn()
        row = conn.execute(
            "SELECT project, content, fact_type, tags, confidence, source, meta FROM facts WHERE id = ? AND valid_until IS NULL",
            (fact_id,),
        ).fetchone()

        if not row:
            raise ValueError(f"Fact {fact_id} not found or inactive")

        project, old_content, fact_type, old_tags_json, confidence, source, old_meta_json = row
        
        # Parse old values safely
        try:
            old_tags = json.loads(old_tags_json) if old_tags_json else []
        except (json.JSONDecodeError, TypeError):
            old_tags = []
            
        try:
            old_meta = json.loads(old_meta_json) if old_meta_json else {}
        except (json.JSONDecodeError, TypeError):
            old_meta = {}

        # Prepare new values
        new_content = content if content is not None else old_content
        new_tags = tags if tags is not None else old_tags
        new_meta = old_meta.copy()
        if meta:
            new_meta.update(meta)
            
        new_meta["previous_fact_id"] = fact_id
        
        # Store as new fact
        new_id = self.store(
            project=project,
            content=new_content,
            fact_type=fact_type,
            tags=new_tags,
            confidence=confidence,
            source=source,
            meta=new_meta,
        )

        # Deprecate old fact
        self.deprecate(fact_id, reason=f"updated_by_{new_id}")
        
        return new_id

    # ─── Graph ────────────────────────────────────────────────────

    def graph(self, project: Optional[str] = None, limit: int = 50) -> dict:
        """Get knowledge graph (entities and relationships)."""
        conn = self._get_conn()
        return get_graph(conn, project, limit)

    def query_entity(self, name: str, project: Optional[str] = None) -> Optional[dict]:
        """Query specific entity in the graph."""
        from cortex.graph import query_entity
        conn = self._get_conn()
        return query_entity(conn, name, project)

    # ─── Search ───────────────────────────────────────────────────

    def search(
        self,
        query: str,
        project: Optional[str] = None,
        top_k: int = 5,
        as_of: Optional[str] = None,
        **kwargs,
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
        if not query or not query.strip():
            raise ValueError("query cannot be empty")
            
        conn = self._get_conn()

        # Try semantic search first
        try:
            embedder = self._get_embedder()
            query_embedding = embedder.embed(query)
            results = semantic_search(
                conn, query_embedding, top_k, project, as_of
            )
            if results:
                return results
        except (ValueError, RuntimeError, sqlite3.Error) as e:
            logger.warning("Semantic search failed, falling back to text: %s", e)

        # Fallback to text search
        return text_search(
            conn, query, project, limit=top_k, fact_type=kwargs.get("fact_type"), tags=kwargs.get("tags")
        )

    # ─── Recall (Project Context) ─────────────────────────────────

    def recall(
        self,
        project: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[Fact]:
        """Load all active facts for a project.

        Args:
            project: Project identifier.
            limit: Max facts to return.
            offset: Pagination offset.
        Returns:
            List of active Facts for the project.
        """
        conn = self._get_conn()
        query = """
            SELECT f.id, f.project, f.content, f.fact_type, f.tags, f.confidence,
                   f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score,
                   f.created_at, f.updated_at, f.tx_id, t.hash
            FROM facts f
            LEFT JOIN transactions t ON f.tx_id = t.id
            WHERE f.project = ? AND f.valid_until IS NULL
            ORDER BY 
                (f.consensus_score * 0.8 + (1.0 / (1.0 + (julianday('now') - julianday(f.created_at)))) * 0.2) DESC,
                f.fact_type, 
                f.created_at DESC
        """
        params = [project]
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        if offset:
            query += " OFFSET ?"
            params.append(offset)

        cursor = conn.execute(query, params)

        return [self._row_to_fact(row) for row in cursor.fetchall()]

    def _verify_fact_tenant(self, fact_id: int, tenant_id: str) -> bool:
        """Lightweight check for fact tenant ownership."""
        conn = self._get_conn()
        row = conn.execute("SELECT project FROM facts WHERE id = ?", (fact_id,)).fetchone()
        return row is not None and row[0] == tenant_id

    def vote(self, fact_id: int, agent: str, value: int, agent_id: Optional[str] = None) -> float:
        """Cast a consensus vote on a fact.

        Args:
            fact_id: The ID of the fact to vote on.
            agent: The name of the agent voting (legacy).
            value: Vote value (1 for verify, -1 for dispute, 0 to remove).
            agent_id: The UUID of the agent (RWC v2). If provided, uses RWC logic.

        Returns:
            The updated consensus_score.
        """
        if agent_id:
            return self.vote_v2(fact_id, agent_id, value)

        # Legacy fallback
        conn = self._get_conn()
        if value == 0:
            conn.execute(
                "DELETE FROM consensus_votes WHERE fact_id = ? AND agent = ?",
                (fact_id, agent),
            )
        else:
            conn.execute(
                "INSERT OR REPLACE INTO consensus_votes (fact_id, agent, vote) VALUES (?, ?, ?)",
                (fact_id, agent, value),
            )
        score = self._recalculate_consensus(fact_id, conn)
        conn.commit()
        logger.info("Agent '%s' voted %d on fact #%d (New score: %.2f)",
                     agent, value, fact_id, score)
        return score

    def register_agent(self, name: str, agent_type: str = "ai", public_key: str = "", tenant_id: str = "default") -> str:
        """Register a new agent for Reputation-Weighted Consensus.

        Returns:
            The unique agent UUID.
        """
        import uuid
        agent_id = str(uuid.uuid4())
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO agents (id, name, agent_type, public_key, tenant_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (agent_id, name, agent_type, public_key, tenant_id),
        )
        conn.commit()
        logger.info("Registered new agent: %s (%s)", name, agent_id)
        return agent_id

    def vote_v2(self, fact_id: int, agent_id: str, value: int, reason: Optional[str] = None) -> float:
        """Cast a reputation-weighted vote (RWC v2)."""
        conn = self._get_conn()
        
        # 1. Fetch agent reputation
        agent = conn.execute(
            "SELECT reputation_score FROM agents WHERE id = ? AND is_active = 1",
            (agent_id,)
        ).fetchone()
        
        if not agent:
            raise ValueError(f"Agent {agent_id} not found or inactive")
        
        rep = agent[0]
        
        if value == 0:
            conn.execute(
                "DELETE FROM consensus_votes_v2 WHERE fact_id = ? AND agent_id = ?",
                (fact_id, agent_id)
            )
        else:
            # 2. Record vote with current reputation snapshot
            conn.execute(
                """
                INSERT OR REPLACE INTO consensus_votes_v2 
                (fact_id, agent_id, vote, vote_weight, agent_rep_at_vote, vote_reason)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (fact_id, agent_id, value, rep, rep, reason)
            )
        
        # 3. Recalculate and commit
        score = self._recalculate_consensus_v2(fact_id, conn)
        conn.commit()
        return score

    def _recalculate_consensus_v2(self, fact_id: int, conn: sqlite3.Connection) -> float:
        """Calculate consensus score using reputation weights."""
        # Query all active votes for this fact
        votes = conn.execute(
            """
            SELECT v.vote, v.vote_weight, a.reputation_score
            FROM consensus_votes_v2 v
            JOIN agents a ON v.agent_id = a.id
            WHERE v.fact_id = ? AND a.is_active = 1
            """,
            (fact_id,)
        ).fetchall()

        if not votes:
            # Fall back to legacy if no v2 votes exist yet? 
            # For now, we'll return the legacy score if v2 is empty
            return self._recalculate_consensus(fact_id, conn)

        weighted_sum = 0.0
        total_weight = 0.0
        
        for vote, vote_weight, current_rep in votes:
            # Use the higher of recorded weight or current reputation
            # (or just current rep depending on policy)
            weight = max(vote_weight, current_rep)
            weighted_sum += vote * weight
            total_weight += weight

        if total_weight > 0:
            normalized = weighted_sum / total_weight  # Range [-1, 1]
            score = 1.0 + normalized  # Scale to [0, 2]
        else:
            score = 1.0

        # Update fact
        new_confidence = None
        if score >= 1.6: new_confidence = "verified"
        elif score <= 0.4: new_confidence = "disputed"
        
        if new_confidence:
            conn.execute(
                "UPDATE facts SET consensus_score = ?, confidence = ? WHERE id = ?",
                (score, new_confidence, fact_id)
            )
        else:
            conn.execute(
                "UPDATE facts SET consensus_score = ? WHERE id = ?",
                (score, fact_id)
            )
            
        return score

    def _recalculate_consensus(self, fact_id: int, conn: sqlite3.Connection) -> float:
        """Update consensus_score based on votes and adjust confidence."""
        row = conn.execute(
            "SELECT SUM(vote) FROM consensus_votes WHERE fact_id = ?",
            (fact_id,),
        ).fetchone()
        vote_sum = row[0] or 0
        # Score starts at 1.0 (neutral). Each vote adds/removes 0.1.
        # Verified threshold: 1.5 (net +5 votes)
        # Disputed threshold: 0.5 (net -5 votes)
        score = max(0.0, 1.0 + (vote_sum * 0.1))

        # Thresholds for automatic confidence shifting
        new_confidence = None
        if score >= 1.5:
            new_confidence = "verified"
        elif score <= 0.5:
            new_confidence = "disputed"

        if new_confidence:
            conn.execute(
                "UPDATE facts SET consensus_score = ?, confidence = ? WHERE id = ?",
                (score, new_confidence, fact_id),
            )
        else:
            conn.execute(
                "UPDATE facts SET consensus_score = ? WHERE id = ?",
                (score, fact_id),
            )
        return score

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
            clause, params = build_temporal_filter_params(as_of, table_alias="f")
            query = """
                SELECT f.id, f.project, f.content, f.fact_type, f.tags, f.confidence,
                       f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score,
                       f.created_at, f.updated_at, f.tx_id, t.hash
                FROM facts f
                LEFT JOIN transactions t ON f.tx_id = t.id
                WHERE f.project = ? AND """ + clause + """
                ORDER BY f.valid_from DESC
                """
            # Combine params safely
            full_params = [project] + params
            cursor = conn.execute(query, full_params)
        else:
            cursor = conn.execute(
                """
                SELECT f.id, f.project, f.content, f.fact_type, f.tags, f.confidence,
                       f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score,
                       f.created_at, f.updated_at, f.tx_id, t.hash
                FROM facts f
                LEFT JOIN transactions t ON f.tx_id = t.id
                WHERE f.project = ?
                ORDER BY f.valid_from DESC
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
        if fact_id <= 0:
            raise ValueError("Invalid fact_id")

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
            logger.info("Deprecated fact #%d", fact_id)
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
    ) -> int:
        """Log an action to the immutable transaction ledger.
        
        Returns:
            The transaction ID (tx_id).
        """
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

        cursor = conn.execute(
            """
            INSERT INTO transactions (project, action, detail, prev_hash, hash, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (project, action, detail_json, prev_hash, tx_hash, ts),
        )
        return cursor.lastrowid

    # ─── Helpers ──────────────────────────────────────────────────

    def _row_to_fact(self, row: tuple) -> Fact:
        """Convert a database row to a Fact object.

        Expected column order:
        id, project, content, fact_type, tags, confidence, valid_from, valid_until, source, meta, consensus_score, 
        created_at, updated_at, tx_id, hash
        """
        try:
            tags = json.loads(row[4]) if row[4] else []
        except (json.JSONDecodeError, TypeError):
            tags = []
            
        try:
            meta = json.loads(row[9]) if row[9] else {}
        except (json.JSONDecodeError, TypeError):
            meta = {}

        return Fact(
            id=row[0],
            project=row[1],
            content=row[2],
            fact_type=row[3],
            tags=tags,
            confidence=row[5],
            valid_from=row[6],
            valid_until=row[7],
            source=row[8],
            meta=meta,
            consensus_score=row[10] if len(row) > 10 else 1.0,
            created_at=row[11] if len(row) > 11 else "unknown",
            updated_at=row[12] if len(row) > 12 else "unknown",
            tx_id=row[13] if len(row) > 13 else None,
            hash=row[14] if len(row) > 14 else None,
        )

    # ─── Wave 6: Temporal Navigation ──────────────────────────────

    def reconstruct_state(self, target_tx_id: int, project: Optional[str] = None) -> list[Fact]:
        """Reconstruct the active database state at a specific transaction ID.
        
        Args:
            target_tx_id: The transaction ID to target.
            project: Optional project scope.
            
        Returns:
            List of Facts that were active at that point.
        """
        conn = self._get_conn()
        
        # 1. Get the timestamp of the target transaction
        tx = conn.execute("SELECT timestamp FROM transactions WHERE id = ?", (target_tx_id,)).fetchone()
        if not tx:
            raise ValueError(f"Transaction ID {target_tx_id} not found")
        
        tx_time = tx[0]
        
        # 2. Query facts that were:
        # - Created BEFORE or AT tx_time
        # - NOT deprecated OR deprecated AFTER tx_time
        # - AND linked to tx_id <= target_tx_id (Precise check)
        
        query = """
            SELECT f.id, f.project, f.content, f.fact_type, f.tags, f.confidence,
                   f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score,
                   f.created_at, f.updated_at, f.tx_id, t.hash
            FROM facts f
            LEFT JOIN transactions t ON f.tx_id = t.id
            WHERE (f.created_at <= ? AND (f.valid_until IS NULL OR f.valid_until > ?))
              AND (f.tx_id IS NULL OR f.tx_id <= ?)
        """
        params = [tx_time, tx_time, target_tx_id]
        
        if project:
            query += " AND project = ?"
            params.append(project)
            
        query += " ORDER BY id ASC"
        
        cursor = conn.execute(query, params)
        return [self._row_to_fact(row) for row in cursor.fetchall()]

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

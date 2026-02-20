import json
import logging
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import aiosqlite

from cortex.canonical import canonical_json, compute_tx_hash
from cortex.connection_pool import CortexConnectionPool
from cortex.consensus.vote_ledger import ImmutableVoteLedger
from cortex.embeddings import LocalEmbedder
from cortex.engine.agent_mixin import AgentMixin
from cortex.engine.ledger import ImmutableLedger
from cortex.engine.search_mixin import SearchMixin

# Mixins
from cortex.engine.store_mixin import StoreMixin
from cortex.graph import get_graph as _get_graph
from cortex.temporal import now_iso

logger = logging.getLogger("cortex.engine.async")

TX_BEGIN_IMMEDIATE = "BEGIN IMMEDIATE"

class AsyncCortexEngine(StoreMixin, SearchMixin, AgentMixin):
    """
    Native async database engine for CORTEX.
    Protocol: MEJORAlo God Mode 8.0 - Wave 3 Structural Correction
    """

    FACT_COLUMNS = (
        "f.id, f.project, f.content, f.fact_type, f.tags, f.confidence, "
        "f.valid_from, f.valid_until, f.source, f.meta, f.consensus_score, "
        "f.created_at, f.updated_at, f.tx_id, t.hash"
    )
    FACT_JOIN = "FROM facts f LEFT JOIN transactions t ON f.tx_id = t.id"

    def __init__(self, pool: CortexConnectionPool, db_path: str):
        self._pool = pool
        self._db_path = Path(db_path)
        self._embedder: LocalEmbedder | None = None
        self._ledger: ImmutableLedger | None = None

        # Mixin configuration
        self._auto_embed = True
        self._vec_available = True  # Assuming local vector availability

    @asynccontextmanager
    async def session(self) -> AsyncIterator[aiosqlite.Connection]:
        """Proporciona una sesión transaccional (conexión) desde el pool."""
        async with self._pool.acquire() as conn:
            yield conn

    def _get_embedder(self) -> LocalEmbedder:
        if self._embedder is None:
            self._embedder = LocalEmbedder()
        return self._embedder

    def _get_ledger(self) -> ImmutableLedger:
        if self._ledger is None:
            self._ledger = ImmutableLedger(self._pool)
        return self._ledger

    async def _log_transaction(self, conn: aiosqlite.Connection, project: str, action: str, detail: dict[str, Any]) -> int:
        dj = canonical_json(detail)
        ts = now_iso()
        async with conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1") as cursor:
            prev = await cursor.fetchone()
            ph = prev[0] if prev else "GENESIS"

        th = compute_tx_hash(ph, project, action, dj, ts)

        cursor = await conn.execute(
            "INSERT INTO transactions (project, action, detail, prev_hash, hash, timestamp) "
            "VALUES (?, ?, ?, COALESCE((SELECT hash FROM transactions ORDER BY id DESC LIMIT 1), 'GENESIS'), ?, ?)",
            (project, action, dj, th, ts)
        )
        # Re-calc hash with actual ph from the DB to be absolute
        async with conn.execute("SELECT prev_hash FROM transactions WHERE id = ?", (cursor.lastrowid,)) as c2:
            row = await c2.fetchone()
            actual_ph = row[0] if row else ph
            if actual_ph != ph:
                # Re-hash if it changed under our feet
                th = compute_tx_hash(actual_ph, project, action, dj, ts)
                await conn.execute("UPDATE transactions SET hash = ? WHERE id = ?", (th, cursor.lastrowid))

        tx_id = cursor.lastrowid
        self._get_ledger().record_write()
        return tx_id

    # store() and deprecate() are now provided by StoreMixin
    # register_agent(), get_agent(), list_agents() are now provided by AgentMixin
    # search() is now provided by SearchMixin

    async def recall(self, project: str, limit: int | None = None) -> list[dict[str, Any]]:
        query = f"""
            SELECT {self.FACT_COLUMNS}
            {self.FACT_JOIN}
            WHERE f.project = ? AND f.valid_until IS NULL
            ORDER BY (
                f.consensus_score * 0.8
                + (1.0 / (1.0 + (julianday('now') - julianday(f.created_at)))) * 0.2
            ) DESC, f.fact_type, f.created_at DESC
        """
        params = [project]
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        async with self.session() as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                results = []
                for row in rows:
                    d = dict(row)
                    d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
                    d["meta"] = json.loads(d["meta"]) if d.get("meta") else {}
                    results.append(d)
                return results

    async def retrieve(self, fact_id: int) -> dict[str, Any]:
        """Retrieve an active fact. Raises FactNotFound if missing or deprecated."""
        fact = await self.get_fact(fact_id)
        if not fact or fact.get("valid_until"):
            from cortex.exceptions import FactNotFound
            raise FactNotFound(f"Fact {fact_id} not found or deprecated")
        return fact

    async def get_fact(self, fact_id: int) -> dict[str, Any] | None:
        async with self.session() as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(f"SELECT {self.FACT_COLUMNS} {self.FACT_JOIN} WHERE f.id = ?", (fact_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                d = dict(row)
                d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
                d["meta"] = json.loads(d["meta"]) if d.get("meta") else {}
                return d

    async def time_travel(self, tx_id: int, project: str | None = None) -> list[dict[str, Any]]:
        """Reconstruct state as of transaction ID."""
        from cortex.temporal import time_travel_filter
        async with self.session() as conn:
            conn.row_factory = aiosqlite.Row
            clause, params = time_travel_filter(tx_id, table_alias="f")
            query = f"SELECT {self.FACT_COLUMNS} {self.FACT_JOIN} WHERE {clause}"
            if project:
                query += " AND f.project = ?"
                params.append(project)
            query += " ORDER BY f.id ASC"
            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                results = []
                for row in rows:
                    d = dict(row)
                    d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
                    d["meta"] = json.loads(d["meta"]) if d.get("meta") else {}
                    results.append(d)
                return results

    async def reconstruct_state(self, tx_id: int, project: str | None = None) -> list[dict[str, Any]]:
        """Alias for time_travel."""
        return await self.time_travel(tx_id, project)

    async def delete_fact(self, fact_id: int) -> bool:
        """Alias for deprecate (Foundation test parity)."""
        return await self.deprecate(fact_id)

    async def vote(self, fact_id: int, agent: str, value: int, signature: str | None = None) -> float:
        """Vote with immutable ledger logging and reputation-weighted consensus."""
        if value not in (-1, 0, 1):
             raise ValueError("Vote must be -1, 0, or 1")

        async with self.session() as conn:
            await conn.execute(TX_BEGIN_IMMEDIATE)
            try:
                # 1. Resolve agent_id (agent parameter is the identifier)
                target_agent_id = agent

                async with conn.execute("SELECT reputation_score FROM agents WHERE id = ?", (target_agent_id,)) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        # Auto-register any agent that reaches the engine (trusting caller)
                        is_human = target_agent_id == "human"
                        initial_rep = 1.0 if is_human else 0.5
                        await conn.execute(
                            "INSERT INTO agents (id, name, agent_type, reputation_score, public_key) VALUES (?, ?, ?, ?, '')",
                            (target_agent_id, target_agent_id.capitalize(), "human" if is_human else "ai", initial_rep)
                        )
                        rep = initial_rep
                    else:
                        rep = row[0]


                # 2. Append to Immutable Vote Ledger
                ledger = ImmutableVoteLedger(conn)

                # Record in consensus table for fast score calculation
                if value == 0:
                     await conn.execute("DELETE FROM consensus_votes_v2 WHERE fact_id = ? AND agent_id = ?", (fact_id, target_agent_id))
                else:
                     await conn.execute(
                         "INSERT OR REPLACE INTO consensus_votes_v2 (fact_id, agent_id, vote, vote_weight, agent_rep_at_vote) VALUES (?, ?, ?, ?, ?)",
                         (fact_id, target_agent_id, value, rep, rep)
                     )

                # Log transaction
                tx_id = await self._log_transaction(conn, "consensus", "vote_v2", {"fact_id": fact_id, "agent_id": target_agent_id, "vote": value})

                # Record in permanent immutable ledger
                await ledger.append_vote(fact_id, target_agent_id, value, rep, signature)

                # Recalculate score
                async with conn.execute(
                    "SELECT v.vote, v.vote_weight, a.reputation_score "
                    "FROM consensus_votes_v2 v "
                    "JOIN agents a ON v.agent_id = a.id "
                    "WHERE v.fact_id = ? AND a.is_active = 1",
                    (fact_id,)
                ) as cursor:
                    votes = await cursor.fetchall()

                if not votes:
                    score = 1.0
                else:
                    weighted_sum = sum(v[0] * max(v[1], v[2]) for v in votes)
                    total_weight = sum(max(v[1], v[2]) for v in votes)
                    score = 1.0 + (weighted_sum / total_weight) if total_weight > 0 else 1.0

                # Update fact
                if score >= 1.5:
                    conf = "verified"
                elif score <= 0.5:
                    conf = "disputed"
                else:
                    conf = "stated"

                await conn.execute(
                    "UPDATE facts SET consensus_score = ?, confidence = ? WHERE id = ?",
                    (score, conf, fact_id)
                )

                await conn.commit()
                return score
            except (sqlite3.Error, OSError, ValueError) as e:
                await conn.rollback()
                raise e

    async def get_votes(self, fact_id: int) -> list[dict[str, Any]]:
        async with self.session() as conn:
            conn.row_factory = aiosqlite.Row
            v2_query = """SELECT 'v2' as type, v.vote, v.agent_id as agent, v.created_at, a.reputation_score
                          FROM consensus_votes_v2 v
                          JOIN agents a ON v.agent_id = a.id
                          WHERE v.fact_id = ?"""
            legacy_query = """SELECT 'legacy' as type, vote, agent, timestamp as created_at, 0.0 as reputation_score
                              FROM consensus_votes
                              WHERE fact_id = ?"""
            results = []
            async with conn.execute(v2_query, (fact_id,)) as cursor:
                results.extend([dict(r) for r in await cursor.fetchall()])
            async with conn.execute(legacy_query, (fact_id,)) as cursor:
                results.extend([dict(r) for r in await cursor.fetchall()])
            return results

    async def stats(self) -> dict[str, Any]:
        async with self.session() as conn:
            async with conn.execute("SELECT COUNT(*) FROM facts") as cursor:
                total = (await cursor.fetchone())[0]
            async with conn.execute("SELECT COUNT(*) FROM facts WHERE valid_until IS NULL") as cursor:
                active = (await cursor.fetchone())[0]
            async with conn.execute("SELECT DISTINCT project FROM facts WHERE valid_until IS NULL") as cursor:
                projects = [p[0] for p in await cursor.fetchall()]
            async with conn.execute("SELECT COUNT(*) FROM transactions") as cursor:
                tx_count = (await cursor.fetchone())[0]

            db_size = self._db_path.stat().st_size / (1024 * 1024) if self._db_path.exists() else 0

            try:
                async with conn.execute("SELECT COUNT(*) FROM fact_embeddings") as cursor:
                    embeddings = (await cursor.fetchone())[0]
            except (sqlite3.Error, OSError, ValueError):
                embeddings = 0

            return {
                "total_facts": total,
                "active_facts": active,
                "deprecated_facts": total - active,
                "projects": projects,
                "project_count": len(projects),
                "transactions": tx_count,
                "embeddings": embeddings,
                "db_path": str(self._db_path),
                "db_size_mb": round(db_size, 2),
            }

    async def verify_ledger(self) -> dict[str, Any]:
        return await self._get_ledger().verify_integrity_async()

    async def create_checkpoint(self) -> int | None:
        return await self._get_ledger().create_checkpoint_async()

    async def verify_vote_ledger(self) -> dict[str, Any]:
        async with self.session() as conn:
            ledger = ImmutableVoteLedger(conn)
            return await ledger.verify_chain_integrity()

    async def get_graph(self, project: str | None = None, limit: int = 50) -> dict[str, Any]:
        async with self.session() as conn:
            return await _get_graph(conn, project, limit)

    async def health_check(self) -> bool:
        try:
            async with self.session() as conn:
                async with conn.execute("SELECT 1") as cursor:
                    await cursor.fetchone()
            return True
        except (sqlite3.Error, OSError, ValueError):
            return False

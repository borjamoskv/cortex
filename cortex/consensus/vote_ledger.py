"""
CORTEX v4.0 — Registro Inmutable de Votos.

Almacenamiento de votos a prueba de manipulaciones criptográficas mediante encadenamiento de hashes y árboles de Merkle.
Parte de la Arquitectura de Soberanía Wave 5.
"""

import hashlib
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from cortex.consensus.merkle import MerkleTree, compute_merkle_root

logger = logging.getLogger("cortex.consensus.ledger")


@dataclass
class VoteEntry:
    id: int
    fact_id: int
    agent_id: str
    vote: int
    vote_weight: float
    prev_hash: str
    hash: str
    timestamp: str
    signature: str | None = None


class ImmutableVoteLedger:
    """
    Motor criptográfico de consenso para CORTEX.
    Garantiza la inmutabilidad de los votos mediante encadenamiento de hashes SHA-256.
    Protocolo: MEJORAlo God Mode 7.3 - Wave 5 Structural Correction
    """

    GENESIS_HASH = "0" * 64
    MERKLE_BATCH_SIZE = 1000

    def __init__(self, pool_or_conn):
        self._db = pool_or_conn

    def _compute_hash(self, prev_hash: str, fact_id: int, agent_id: str, vote: int, weight: float, ts: str) -> str:
        """Cálculo determinista del hash del bloque/voto."""
        payload = f"{prev_hash}:{fact_id}:{agent_id}:{vote}:{weight}:{ts}"
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    async def _get_conn(self):
        """Helper para obtener una conexión ya sea desde un pool o una conexión existente."""
        if hasattr(self._db, "acquire"):
             return await self._db.acquire().__aenter__()
        return self._db

    async def _release_conn(self, conn):
        """Libera la conexión si proviene de un pool."""
        if hasattr(self._db, "release"):
            await self._db.release(conn)
        elif hasattr(self._db, "acquire"):
            # Si entramos con __aenter__, salimos con __aexit__ (cerrado por caller o manual)
            pass

    async def append_vote(
        self,
        fact_id: int,
        agent_id: str,
        vote: int,
        vote_weight: float = 1.0,
        signature: str | None = None
    ) -> VoteEntry:
        """
        Añade un voto de forma segura y sellada.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        conn = await self._get_conn()

        should_commit = hasattr(self._db, "acquire")
        if should_commit:
            await conn.execute("BEGIN IMMEDIATE")

        try:
            cursor = await conn.execute(
                "SELECT hash FROM vote_ledger ORDER BY id DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            prev_hash = row[0] if row else self.GENESIS_HASH

            entry_hash = self._compute_hash(prev_hash, fact_id, agent_id, vote, vote_weight, timestamp)

            cursor = await conn.execute(
                """
                INSERT INTO vote_ledger 
                (fact_id, agent_id, vote, vote_weight, prev_hash, hash, timestamp, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (fact_id, agent_id, vote, vote_weight, prev_hash, entry_hash, timestamp, signature)
            )

            vote_id = cursor.lastrowid

            if should_commit:
                await conn.commit()

            logger.info(f"Voto inmutable sellado: Fact {fact_id} | Agent {agent_id} | Hash {entry_hash[:8]}...")
            await self._maybe_create_checkpoint(conn)

            return VoteEntry(
                id=vote_id, fact_id=fact_id, agent_id=agent_id,
                vote=vote, vote_weight=vote_weight, prev_hash=prev_hash,
                hash=entry_hash, timestamp=timestamp, signature=signature
            )
        except (sqlite3.Error, OSError) as e:
            if should_commit:
                await conn.rollback()
            logger.error(f"Fallo al registrar voto inmutable: {e}")
            raise
        finally:
            await self._release_conn(conn)

    async def verify_chain_integrity(self) -> dict[str, Any]:
        """
        Audita toda la cadena de votos.
        """
        violations = []
        conn = await self._get_conn()
        try:
            cursor = await conn.execute(
                "SELECT id, prev_hash, hash, fact_id, agent_id, vote, vote_weight, timestamp "
                "FROM vote_ledger ORDER BY id ASC"
            )
            rows = await cursor.fetchall()

            expected_prev = self.GENESIS_HASH
            for row in rows:
                v_id, p_hash, c_hash, f_id, a_id, v_val, weight, ts = row
                if p_hash != expected_prev:
                    violations.append({
                        "vote_id": v_id,
                        "type": "CHAIN_BREAK",
                        "expected_prev": expected_prev,
                        "actual_prev": p_hash
                    })

                actual_hash = self._compute_hash(p_hash, f_id, a_id, v_val, weight, ts)
                if actual_hash != c_hash:
                    violations.append({
                        "vote_id": v_id,
                        "type": "DATA_TAMPERING",
                        "expected_hash": c_hash,
                        "actual_hash": actual_hash
                    })

                expected_prev = c_hash

            return {
                "valid": len(violations) == 0,
                "violations": violations,
                "votes_checked": len(rows)
            }
        finally:
            await self._release_conn(conn)

    async def _maybe_create_checkpoint(self, conn: aiosqlite.Connection):
        """Verifica si es necesario crear un punto de control de Merkle."""
        async with conn.execute(
            "SELECT COUNT(v.id) FROM vote_ledger v "
            "LEFT JOIN vote_merkle_roots r ON v.id >= r.vote_start_id AND v.id <= r.vote_end_id "
            "WHERE r.id IS NULL"
        ) as cursor:
            count = (await cursor.fetchone())[0]

        if count >= self.MERKLE_BATCH_SIZE:
            await self._create_checkpoint_internal(conn)

    async def create_checkpoint(self) -> str | None:
        """Dispara manualmente un punto de control."""
        conn = await self._get_conn()
        try:
            should_commit = hasattr(self._db, "acquire")
            if should_commit:
                await conn.execute("BEGIN IMMEDIATE")

            root = await self._create_checkpoint_internal(conn)

            if should_commit:
                await conn.commit()
            return root
        except (sqlite3.Error, OSError) as e:
            if should_commit:
                await conn.rollback()
            raise e
        finally:
            await self._release_conn(conn)

    async def _create_checkpoint_internal(self, conn: aiosqlite.Connection) -> str | None:
        """Lógica interna de creación de punto de control."""
        async with conn.execute("SELECT MAX(vote_end_id) FROM vote_merkle_roots") as cursor:
            row = await cursor.fetchone()
            start_id = (row[0] + 1) if row and row[0] is not None else 1

        async with conn.execute(
            "SELECT hash, id FROM vote_ledger WHERE id >= ? ORDER BY id LIMIT ?",
            (start_id, self.MERKLE_BATCH_SIZE)
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return None

        hashes = [r[0] for r in rows]
        end_id = rows[-1][1]

        tree = MerkleTree(hashes)
        root_hash = tree.root

        ts = datetime.now(timezone.utc).isoformat()
        await conn.execute(
            "INSERT INTO vote_merkle_roots (vote_start_id, vote_end_id, root_hash, vote_count, created_at) VALUES (?, ?, ?, ?, ?)",
            (start_id, end_id, root_hash, len(hashes), ts)
        )

        logger.info(f"Punto de control Merkle creado: {start_id}-{end_id} -> {root_hash}")
        return root_hash

    async def verify_merkle_roots(self) -> list[dict[str, Any]]:
        """Verifica todas las raíces Merkle almacenadas."""
        results = []
        conn = await self._get_conn()
        try:
            async with conn.execute("SELECT id, vote_start_id, vote_end_id, root_hash FROM vote_merkle_roots ORDER BY id") as cursor:
                checkpoints = await cursor.fetchall()

            for cp_id, start, end, stored_root in checkpoints:
                async with conn.execute(
                    "SELECT hash FROM vote_ledger WHERE id >= ? AND id <= ? ORDER BY id",
                    (start, end)
                ) as cursor:
                    hashes = [r[0] for r in await cursor.fetchall()]

                recomputed = compute_merkle_root(hashes)
                is_valid = (recomputed == stored_root)

                results.append({
                    "checkpoint_id": cp_id,
                    "range": f"{start}-{end}",
                    "valid": is_valid,
                    "expected": stored_root,
                    "actual": recomputed
                })

            return results
        finally:
            await self._release_conn(conn)

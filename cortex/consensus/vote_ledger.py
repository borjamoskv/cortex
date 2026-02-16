"""
CORTEX v4.0 — Immutable Vote Ledger.

Cryptographically tamper-evident vote storage using hash chaining and Merkle trees.
Part of the Wave 5 Sovereignty Architecture.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

import aiosqlite

logger = logging.getLogger(__name__)


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
    signature: Optional[str] = None


class ImmutableVoteLedger:
    """
    Cryptographically tamper-evident vote storage.
    
    Each vote is chained via SHA-256(prev_hash + current_data).
    Any modification breaks the chain, detectable via verify_chain().
    """
    
    MERKLE_BATCH_SIZE = 1000
    
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def append_vote(
        self,
        fact_id: int,
        agent_id: str,
        vote: int,
        vote_weight: float,
        signature: Optional[str] = None
    ) -> VoteEntry:
        """Append a vote to the immutable ledger."""
        
        # Get previous hash (GENESIS if empty)
        async with self.conn.execute(
            "SELECT hash FROM vote_ledger ORDER BY id DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            prev_hash = row[0] if row else "GENESIS"
        
        timestamp = datetime.utcnow().isoformat()
        
        # Compute hash: SHA256(prev_hash:fact_id:agent_id:vote:weight:timestamp)
        hash_input = f"{prev_hash}:{fact_id}:{agent_id}:{vote}:{vote_weight}:{timestamp}"
        entry_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        # Insert vote
        cursor = await self.conn.execute(
            """
            INSERT INTO vote_ledger 
            (fact_id, agent_id, vote, vote_weight, prev_hash, hash, timestamp, signature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (fact_id, agent_id, vote, vote_weight, prev_hash, entry_hash, timestamp, signature)
        )
        await self.conn.commit()
        
        # TODO: Trigger Merkle checkpoint if batch size reached (async background task)
        # await self._maybe_create_checkpoint() 
        
        return VoteEntry(
            id=cursor.lastrowid,
            fact_id=fact_id,
            agent_id=agent_id,
            vote=vote,
            vote_weight=vote_weight,
            prev_hash=prev_hash,
            hash=entry_hash,
            timestamp=timestamp,
            signature=signature
        )

    async def verify_chain_integrity(self) -> dict:
        """
        Verify the cryptographic integrity of the entire vote ledger.
        
        Returns:
            {
                "valid": bool,
                "violations": [...],
                "votes_checked": int
            }
        """
        violations = []
        
        # 1. Verify hash chain continuity
        async with self.conn.execute(
            "SELECT id, prev_hash, hash, fact_id, agent_id, vote, vote_weight, timestamp "
            "FROM vote_ledger ORDER BY id"
        ) as cursor:
            rows = await cursor.fetchall()
        
        prev_hash = "GENESIS"
        for row in rows:
            vote_id, tx_prev, tx_hash, fact_id, agent_id, vote_val, weight, ts = row
            
            # Verify prev_hash matches
            if tx_prev != prev_hash:
                violations.append({
                    "vote_id": vote_id,
                    "type": "chain_break",
                    "expected_prev": prev_hash,
                    "actual_prev": tx_prev
                })
            
            # Verify current hash computation
            hash_input = f"{tx_prev}:{fact_id}:{agent_id}:{vote_val}:{weight}:{ts}"
            computed = hashlib.sha256(hash_input.encode()).hexdigest()
            
            if computed != tx_hash:
                violations.append({
                    "vote_id": vote_id,
                    "type": "hash_mismatch",
                    "computed": computed,
                    "stored": tx_hash
                })
            
            prev_hash = tx_hash
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "votes_checked": len(rows)
        }

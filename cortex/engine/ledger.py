"""
CORTEX v4.1 — Immutable Ledger with Adaptive Checkpointing.

Cryptographic integrity for the CORTEX transaction ledger using Merkle Trees.
Enables efficient batch verification and tamper-proof auditing.

Adaptive checkpointing: reduces batch size during high write-rate periods
(e.g., swarm bursts) to minimize data loss on crash.
"""

import hashlib
import json
import logging
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple


from cortex.canonical import compute_tx_hash, compute_tx_hash_v1
from cortex.config import CHECKPOINT_MAX, CHECKPOINT_MIN

logger = logging.getLogger("cortex")


@dataclass
class MerkleNode:
    """A node in the Merkle Tree."""

    hash: str
    left: Optional["MerkleNode"] = None
    right: Optional["MerkleNode"] = None
    is_leaf: bool = False


class MerkleTree:
    """
    Merkle tree for batch transaction verification.
    """

    def __init__(self, leaves: List[str]):
        """
        Build a Merkle tree from leaf hashes.
        """
        if not leaves:
            self.leaves = []
            self.root = None
            return

        self.leaves = leaves
        self.root = self._build_tree([MerkleNode(h, is_leaf=True) for h in leaves])

    def _hash_pair(self, left: str, right: str) -> str:
        """Hash two child hashes together."""
        combined = left + right
        return hashlib.sha256(combined.encode()).hexdigest()

    def _build_tree(self, nodes: List[MerkleNode]) -> MerkleNode:
        """Recursively build the tree bottom-up."""
        if len(nodes) == 1:
            return nodes[0]

        next_level = []
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i + 1] if i + 1 < len(nodes) else left

            combined_hash = self._hash_pair(left.hash, right.hash)
            next_level.append(MerkleNode(hash=combined_hash, left=left, right=right))

        return self._build_tree(next_level)

    def get_root(self) -> Optional[str]:
        """Get the root hash of the tree."""
        return self.root.hash if self.root else None

    def get_proof(self, index: int) -> List[Tuple[str, str]]:
        """Get a Merkle proof for a leaf at the given index."""
        if not self.root or index >= len(self.leaves):
            return []

        proof = []
        current_idx = index
        current_level = [MerkleNode(h, is_leaf=True) for h in self.leaves]

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left

                if i == current_idx or (i + 1 == current_idx and i + 1 < len(current_level)):
                    if current_idx == i:
                        proof.append((right.hash, "R"))
                    else:
                        proof.append((left.hash, "L"))

                combined_hash = self._hash_pair(left.hash, right.hash)
                next_level.append(MerkleNode(hash=combined_hash, left=left, right=right))

            current_idx //= 2
            current_level = next_level

        return proof

    @staticmethod
    def verify_proof(leaf_hash: str, proof: List[Tuple[str, str]], root: str) -> bool:
        """Verify a Merkle proof against a root hash."""
        # This is a static method that can be used without an instance
        current = leaf_hash
        for sibling, direction in proof:
            if direction == "L":
                combined = sibling + current
            else:
                combined = current + sibling
            current = hashlib.sha256(combined.encode()).hexdigest()
        return current == root


class ImmutableLedger:
    """
    Manages the cryptographic integrity of the CORTEX transaction ledger.

    Adaptive checkpointing: batch size shrinks during high write-rate
    periods (swarm bursts) and returns to normal during calm periods.
    """

    CHECKPOINT_BATCH_SIZE = CHECKPOINT_MAX  # Legacy compat (class attribute)
    WRITE_RATE_WINDOW = 60  # seconds
    HIGH_WRITE_THRESHOLD = 10  # writes/sec triggers adaptive reduction

    def __init__(self, pool: "CortexConnectionPool"):
        self.pool = pool
        self._write_timestamps: deque[float] = deque(maxlen=5000)

    def record_write(self) -> None:
        """Call on every transaction to track write rate."""
        self._write_timestamps.append(time.monotonic())

    @property
    def adaptive_batch_size(self) -> int:
        """Compute batch size based on recent write rate."""
        now = time.monotonic()
        cutoff = now - self.WRITE_RATE_WINDOW
        recent = sum(1 for t in self._write_timestamps if t > cutoff)
        rate = recent / self.WRITE_RATE_WINDOW
        if rate > self.HIGH_WRITE_THRESHOLD:
            return CHECKPOINT_MIN
        return CHECKPOINT_MAX

    async def compute_merkle_root_async(self, start_id: int, end_id: int) -> Optional[str]:
        """Compute Merkle root for a range of transactions (async)."""
        async with self.pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT hash FROM transactions WHERE id >= ? AND id <= ? ORDER BY id",
                (start_id, end_id),
            )
            rows = await cursor.fetchall()
            hashes = [row[0] for row in rows]
            if not hashes:
                return None

            tree = MerkleTree(hashes)
            return tree.get_root()

    async def create_checkpoint_async(self) -> Optional[int]:
        """Create a Merkle tree checkpoint for recent transactions (async)."""
        batch_size = self.adaptive_batch_size

        async with self.pool.acquire() as conn:
            # Find last checkpointed transaction
            cursor = await conn.execute("SELECT MAX(tx_end_id) FROM merkle_roots")
            row = await cursor.fetchone()
            last_tx = row[0] or 0 if row else 0

            # Count pending transactions
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE id > ?", (last_tx,)
            )
            row = await cursor.fetchone()
            pending = row[0] if row else 0

            if pending < batch_size:
                return None

            start_id = last_tx + 1
            # Get the ID of the N-th transaction from start
            cursor = await conn.execute(
                "SELECT id FROM transactions WHERE id >= ? ORDER BY id LIMIT 1 OFFSET ?",
                (start_id, batch_size - 1),
            )
            end_row = await cursor.fetchone()

            if not end_row:
                return None

            end_id = end_row[0]

            # Compute Merkle Root (uses its own acquisition, but we are inside one here)
            # Actually, compute_merkle_root_async should probably take a conn to avoid deadlocks/extra overhead
            # But since pool is async, it's fine.
            root_hash = await self.compute_merkle_root_async(start_id, end_id)

            if not root_hash:
                return None

            cursor = await conn.execute(
                """
                INSERT INTO merkle_roots (root_hash, tx_start_id, tx_end_id, tx_count)
                VALUES (?, ?, ?, ?)
                """,
                (root_hash, start_id, end_id, batch_size),
            )
            await conn.commit()
            logger.info(
                "Created Merkle checkpoint #%d (TX %d-%d)", cursor.lastrowid, start_id, end_id
            )
            return cursor.lastrowid

    async def verify_integrity_async(self) -> dict:
        """Verify hash chain continuity and Merkle checkpoints (async)."""
        violations = []

        async with self.pool.acquire() as conn:
            # 1. Verify Hash Chain
            cursor = await conn.execute(
                "SELECT id, prev_hash, hash, project, action, detail, timestamp FROM transactions ORDER BY id"
            )
            txs = await cursor.fetchall()

            current_prev = "GENESIS"
            for tx_id, p_hash, c_hash, proj, act, detail, ts in txs:
                if p_hash != current_prev:
                    violations.append(
                        {
                            "tx_id": tx_id,
                            "type": "chain_break",
                            "expected": current_prev,
                            "actual": p_hash,
                        }
                    )

                # Recompute hash — try v2 (canonical) first, fallback to v1 (legacy)
                computed_v2 = compute_tx_hash(p_hash, proj, act, detail, ts)
                computed_v1 = compute_tx_hash_v1(p_hash, proj, act, detail, ts)
                if computed_v2 != c_hash and computed_v1 != c_hash:
                    violations.append(
                        {
                            "tx_id": tx_id,
                            "type": "hash_mismatch",
                            "computed_v2": computed_v2,
                            "computed_v1": computed_v1,
                            "stored": c_hash,
                        }
                    )
                current_prev = c_hash

            # 2. Verify Merkle Checkpoints
            cursor = await conn.execute(
                "SELECT id, root_hash, tx_start_id, tx_end_id FROM merkle_roots ORDER BY id"
            )
            roots = await cursor.fetchall()

            for m_id, r_hash, start, end in roots:
                # We reuse the same compute method
                computed_r = await self.compute_merkle_root_async(start, end)
                if computed_r != r_hash:
                    violations.append(
                        {
                            "merkle_id": m_id,
                            "type": "merkle_mismatch",
                            "expected": r_hash,
                            "actual": computed_r,
                        }
                    )

            status = "ok" if not violations else "violation"

            if violations:
                logger.error(f"Integrity check failed: {len(violations)} violations found")

            # Record check
            await conn.execute(
                "INSERT INTO integrity_checks (check_type, status, details, started_at, completed_at) VALUES (?, ?, ?, ?, ?)",
                (
                    "full",
                    status,
                    json.dumps(violations),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )
            await conn.commit()

            return {
                "valid": not violations,
                "violations": violations,
                "tx_checked": len(txs),
                "roots_checked": len(roots),
            }

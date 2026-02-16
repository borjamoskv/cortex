"""
CORTEX v4.0 — Immutable Ledger.

Cryptographic integrity for the CORTEX transaction ledger using Merkle Trees.
Enables efficient batch verification and tamper-proof auditing.
"""

import hashlib
import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

logger = logging.getLogger("cortex")

@dataclass
class MerkleNode:
    """A node in the Merkle Tree."""
    hash: str
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None
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
                        proof.append((right.hash, 'R'))
                    else:
                        proof.append((left.hash, 'L'))
                
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
            if direction == 'L':
                combined = sibling + current
            else:
                combined = current + sibling
            current = hashlib.sha256(combined.encode()).hexdigest()
        return current == root

class ImmutableLedger:
    """
    Manages the cryptographic integrity of the CORTEX transaction ledger.
    """
    CHECKPOINT_BATCH_SIZE = 1000

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def compute_merkle_root(self, start_id: int, end_id: int) -> Optional[str]:
        """Compute Merkle root for a range of transactions."""
        cursor = self.conn.execute(
            "SELECT hash FROM transactions WHERE id >= ? AND id <= ? ORDER BY id",
            (start_id, end_id)
        )
        hashes = [row[0] for row in cursor.fetchall()]
        if not hashes:
            return None
            
        tree = MerkleTree(hashes)
        return tree.get_root()

    def create_checkpoint(self) -> Optional[int]:
        """Create a Merkle tree checkpoint for recent transactions."""
        # Find last checkpointed transaction
        last_tx = self.conn.execute(
            "SELECT MAX(tx_end_id) FROM merkle_roots"
        ).fetchone()[0] or 0
        
        # Count pending transactions
        pending = self.conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE id > ?",
            (last_tx,)
        ).fetchone()[0]
        
        if pending < self.CHECKPOINT_BATCH_SIZE:
            logger.debug("Not enough transactions for a checkpoint (%d/%d)", pending, self.CHECKPOINT_BATCH_SIZE)
            return None
            
        start_id = last_tx + 1
        # Get the ID of the N-th transaction from start
        end_row = self.conn.execute(
            "SELECT id FROM transactions WHERE id >= ? ORDER BY id LIMIT 1 OFFSET ?",
            (start_id, self.CHECKPOINT_BATCH_SIZE - 1)
        ).fetchone()
        
        if not end_row:
            return None
            
        end_id = end_row[0]
        root_hash = self.compute_merkle_root(start_id, end_id)
        
        if not root_hash:
            return None
            
        cursor = self.conn.execute(
            """
            INSERT INTO merkle_roots (root_hash, tx_start_id, tx_end_id, tx_count)
            VALUES (?, ?, ?, ?)
            """,
            (root_hash, start_id, end_id, self.CHECKPOINT_BATCH_SIZE)
        )
        self.conn.commit()
        logger.info("Created Merkle checkpoint #%d (TX %d-%d)", cursor.lastrowid, start_id, end_id)
        return cursor.lastrowid

    def verify_integrity(self) -> dict:
        """Verify hash chain continuity and Merkle checkpoints."""
        violations = []
        
        # 1. Verify Hash Chain
        txs = self.conn.execute(
            "SELECT id, prev_hash, hash, project, action, detail, timestamp FROM transactions ORDER BY id"
        ).fetchall()
        
        current_prev = "GENESIS"
        for tx_id, p_hash, c_hash, proj, act, detail, ts in txs:
            if p_hash != current_prev:
                violations.append({
                    "tx_id": tx_id,
                    "type": "chain_break",
                    "expected": current_prev,
                    "actual": p_hash
                })
            
            # Recompute hash
            h_input = f"{p_hash}:{proj}:{act}:{detail}:{ts}"
            computed = hashlib.sha256(h_input.encode()).hexdigest()
            if computed != c_hash:
                violations.append({
                    "tx_id": tx_id,
                    "type": "hash_mismatch",
                    "computed": computed,
                    "stored": c_hash
                })
            current_prev = c_hash
            
        # 2. Verify Merkle Checkpoints
        roots = self.conn.execute(
            "SELECT id, root_hash, tx_start_id, tx_end_id FROM merkle_roots ORDER BY id"
        ).fetchall()
        
        for m_id, r_hash, start, end in roots:
            computed_r = self.compute_merkle_root(start, end)
            if computed_r != r_hash:
                violations.append({
                    "merkle_id": m_id,
                    "type": "merkle_mismatch",
                    "expected": r_hash,
                    "actual": computed_r
                })
                
        status = "ok" if not violations else "violation"
        
        # Record check
        self.conn.execute(
            "INSERT INTO integrity_checks (check_type, status, details, started_at, completed_at) VALUES (?, ?, ?, ?, ?)",
            ("full", status, json.dumps(violations), datetime.now().isoformat(), datetime.now().isoformat())
        )
        self.conn.commit()
        
        return {
            "valid": not violations,
            "violations": violations,
            "tx_checked": len(txs),
            "roots_checked": len(roots)
        }

"""
CORTEX v4.0 — Merkle Tree Utilities.

Provides Merkle tree computation and verification for ledger checkpoints.
"""

import hashlib
from typing import List, Tuple


def compute_merkle_root(hashes: List[str]) -> str:
    """
    Compute the Merkle root of a list of hashes.

    Args:
        hashes: List of SHA-256 hex strings.

    Returns:
        Hex string of the Merkle root.
    """
    if not hashes:
        return ""

    current_level = hashes

    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            # Handle odd number of elements by duplicating the last one
            right = current_level[i + 1] if i + 1 < len(current_level) else left

            combined = f"{left}{right}"
            next_hash = hashlib.sha256(combined.encode()).hexdigest()
            next_level.append(next_hash)
        current_level = next_level

    return current_level[0]


def verify_merkle_proof(leaf_hash: str, proof: List[Tuple[str, str]], root_hash: str) -> bool:
    """
    Verify a Merkle inclusion proof.

    Args:
        leaf_hash: The hash of the item to verify.
        proof: List of (sibling_hash, position) tuples. Position is 'L' (left) or 'R' (right).
        root_hash: The expected Merkle root.

    Returns:
        True if the proof is valid.
    """
    current_hash = leaf_hash

    for sibling, position in proof:
        if position == "L":
            combined = f"{sibling}{current_hash}"
        else:
            combined = f"{current_hash}{sibling}"

        current_hash = hashlib.sha256(combined.encode()).hexdigest()


class MerkleTree:
    """
    A simple Merkle tree implementation for batch verification.
    """

    def __init__(self, items: List[str]):
        self.leaves = items
        self.tree = self._build_tree(items)

    def _build_tree(self, hashes: List[str]) -> List[List[str]]:
        if not hashes:
            return [[""]]

        tree = [hashes]
        current_level = hashes

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left

                combined = f"{left}{right}"
                next_hash = hashlib.sha256(combined.encode()).hexdigest()
                next_level.append(next_hash)
            tree.append(next_level)
            current_level = next_level

        return tree

    @property
    def root(self) -> str:
        """Return the root hash of the tree."""
        return self.tree[-1][0] if self.tree and self.tree[-1] else ""

    def get_proof(self, index: int) -> List[Tuple[str, str]]:
        """
        Get a Merkle proof for the leaf at 'index'.

        Returns:
            List of (sibling_hash, position) tuples.
        """
        if index < 0 or index >= len(self.leaves):
            return []

        proof = []
        current_index = index

        for level in self.tree[:-1]:
            # Sibling is at current_index ^ 1 (bitwise XOR)
            sibling_index = current_index ^ 1

            if sibling_index < len(level):
                sibling_hash = level[sibling_index]
                position = "R" if current_index % 2 == 0 else "L"
                proof.append((sibling_hash, position))
            else:
                # If no sibling (odd element at end), it duplicates itself for the hash
                # but the proof needs the self-hash to combine.
                # In this implementation, the parent is H(left, left).
                # So the sibling is effectively the left node itself.
                proof.append((level[current_index], "R"))

            current_index //= 2

        return proof

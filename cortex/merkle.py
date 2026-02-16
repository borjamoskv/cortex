import hashlib
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class MerkleNode:
    """A node in the Merkle Tree."""

    hash: str
    left: Optional["MerkleNode"] = None
    right: Optional["MerkleNode"] = None
    is_leaf: bool = False


class MerkleTree:
    """
    Merkle tree for batch verification.
    Shared by transaction ledger and vote ledger.
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
        current = leaf_hash
        for sibling, direction in proof:
            if direction == "L":
                combined = sibling + current
            else:
                combined = current + sibling
            current = hashlib.sha256(combined.encode()).hexdigest()
        return current == root

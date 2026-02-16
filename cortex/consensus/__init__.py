"""
CORTEX v4.0 — Consensus Layer.

Provides immutable vote ledger, Merkle tree verification, and consensus protocols.
"""

from .merkle import MerkleTree, compute_merkle_root, verify_merkle_proof
from .vote_ledger import ImmutableVoteLedger, VoteEntry

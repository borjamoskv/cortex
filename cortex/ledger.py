"""CORTEX v4.0 — Immutable Ledger (re-export bridge).

The canonical implementation lives in ``cortex.engine.ledger``.
This module re-exports for backward compatibility.
"""

from cortex.engine.ledger import (  # noqa: F401
    ImmutableLedger,
    MerkleNode,
    MerkleTree,
)

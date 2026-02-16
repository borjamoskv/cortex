"""CORTEX v4.0 — Canonical Hash Construction.

Provides deterministic JSON serialization and null-byte separated
hash computation for the transaction ledger. Hardens against
preimage and collision attacks on the hash chain.

Hash Scheme Versions:
    v1: colon-delimited   f"{prev}:{project}:{action}:{detail}:{ts}"
    v2: null-byte canon   f"{prev}\\x00{project}\\x00{action}\\x00{canonical_detail}\\x00{ts}"
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# ─── Canonical JSON ───────────────────────────────────────────────


def canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, no whitespace, ASCII-safe.

    Guarantees identical output for semantically identical input
    regardless of Python dict insertion order.

    Args:
        obj: Any JSON-serializable object.

    Returns:
        Canonical JSON string.
    """
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, default=str,
    )


# ─── Transaction Hash ────────────────────────────────────────────

HASH_VERSION = 2


def compute_tx_hash(
    prev_hash: str,
    project: str,
    action: str,
    detail_json: str,
    timestamp: str,
) -> str:
    """Compute transaction hash using null-byte separated canonical form.

    Uses \\x00 (null byte) as field separator to prevent boundary
    confusion when fields contain colons or other delimiters.

    Args:
        prev_hash: Hash of the previous transaction, or "GENESIS".
        project: Project identifier.
        action: Transaction action (store, deprecate, vote, etc.).
        detail_json: Canonical JSON string of transaction detail.
        timestamp: ISO 8601 UTC timestamp.

    Returns:
        SHA-256 hex digest of the canonical input.
    """
    h_input = (
        f"{prev_hash}\x00{project}\x00{action}"
        f"\x00{detail_json}\x00{timestamp}"
    )
    return hashlib.sha256(h_input.encode("utf-8")).hexdigest()


def compute_tx_hash_v1(
    prev_hash: str,
    project: str,
    action: str,
    detail_json: str,
    timestamp: str,
) -> str:
    """Legacy v1 hash: colon-delimited concatenation.

    Kept for backward-compatible verification of transactions
    created before the canonical hash migration.
    """
    h_input = f"{prev_hash}:{project}:{action}:{detail_json}:{timestamp}"
    return hashlib.sha256(h_input.encode()).hexdigest()

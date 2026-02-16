"""
CORTEX v4.0 — Temporal Fact Management.

Handles versioned facts with valid_from/valid_until semantics.
Never deletes — only deprecates. Enables time-travel queries.
"""

from __future__ import annotations

from datetime import datetime, timezone


def now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def is_valid_at(valid_from: str, valid_until: str | None, at: str | None = None) -> bool:
    """Check if a fact is valid at a specific point in time.

    Args:
        valid_from: ISO 8601 timestamp when fact became valid.
        valid_until: ISO 8601 timestamp when fact was deprecated (None = still valid).
        at: ISO 8601 timestamp to check against (None = now).

    Returns:
        True if the fact was valid at the given time.
    """
    check_time = at or now_iso()

    if valid_from > check_time:
        return False

    if valid_until is not None and valid_until <= check_time:
        return False

    return True


def build_temporal_filter_params(
    as_of: str | None = None,
    table_alias: str | None = None,
) -> tuple[str, list]:
    """Build parameterized SQL WHERE clause for temporal filtering.

    Args:
        as_of: ISO 8601 timestamp. None = current facts only.
        table_alias: Optional table alias prefix (e.g. "f" → "f.valid_from").
                     If None, uses bare column names.

    Returns:
        Tuple of (SQL WHERE clause, parameters list).

    Raises:
        ValueError: If table_alias contains non-alphanumeric characters.
    """
    # Defense-in-depth: whitelist the alias to prevent injection
    if table_alias is not None:
        if not table_alias.isalnum():
            raise ValueError(f"Invalid table alias: {table_alias!r}")
        prefix = f"{table_alias}."
    else:
        prefix = ""

    if as_of is None:
        return f"{prefix}valid_until IS NULL", []
    else:
        return (
            f"{prefix}valid_from <= ? AND ({prefix}valid_until IS NULL OR {prefix}valid_until > ?)",
            [as_of, as_of],
        )


def time_travel_filter(
    tx_id: int,
    table_alias: str | None = None,
) -> tuple[str, list]:
    """Build SQL WHERE clause to reconstruct fact state at a specific transaction.

    Returns facts whose ``tx_id`` is at or before the target transaction
    and that had not yet been deprecated at that point.

    Args:
        tx_id: Transaction ID to travel to.
        table_alias: Optional table alias prefix.

    Returns:
        Tuple of (SQL WHERE clause, parameters list).

    Raises:
        ValueError: If tx_id is not a positive integer or alias is unsafe.
    """
    if not isinstance(tx_id, int) or tx_id <= 0:
        raise ValueError(f"Invalid tx_id: {tx_id!r}")

    if table_alias is not None:
        if not table_alias.isalnum():
            raise ValueError(f"Invalid table alias: {table_alias!r}")
        prefix = f"{table_alias}."
    else:
        prefix = ""

    return (
        f"{prefix}tx_id <= ? AND ("
        f"{prefix}valid_until IS NULL OR "
        f"{prefix}valid_until > (SELECT timestamp FROM transactions WHERE id = ?))",
        [tx_id, tx_id],
    )

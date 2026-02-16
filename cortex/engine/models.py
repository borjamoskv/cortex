"""CORTEX Engine — Fact Model and helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class Fact:
    id: int
    project: str
    content: str
    fact_type: str
    tags: list[str]
    confidence: str
    valid_from: str
    valid_until: Optional[str]
    source: Optional[str]
    meta: dict
    created_at: str
    updated_at: str
    consensus_score: float = 1.0
    tx_id: Optional[int] = None
    hash: Optional[str] = None

    def is_active(self) -> bool:
        return self.valid_until is None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project": self.project,
            "content": self.content,
            "type": self.fact_type,
            "tags": self.tags,
            "confidence": self.confidence,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "source": self.source,
            "active": self.is_active(),
            "consensus_score": self.consensus_score,
        }


def row_to_fact(row: tuple) -> Fact:
    # Safely handle JSON parsing
    try:
        tags = json.loads(row[4]) if row[4] else []
    except (json.JSONDecodeError, TypeError):
        tags = []

    try:
        meta = json.loads(row[9]) if row[9] else {}
    except (json.JSONDecodeError, TypeError):
        meta = {}

    # Handle shorter tuples safely (legacy tests might pass incomplete rows)
    # Schema expects 15 columns (indices 0-14)
    # If row is short, fill with defaults
    r = list(row)
    while len(r) < 15:
        r.append(None)

    # Defaults for non-nullable fields if missing/None from DB (shouldn't happen in real DB but maybe in mocks)
    # consensus_score index 10
    score = r[10] if r[10] is not None else 1.0

    return Fact(
        id=r[0],
        project=r[1],
        content=r[2],
        fact_type=r[3],
        tags=tags,
        confidence=r[5],
        valid_from=r[6],
        valid_until=r[7],
        source=r[8],
        meta=meta,
        consensus_score=score,
        created_at=r[11],
        updated_at=r[12],
        tx_id=r[13],
        hash=r[14],
    )

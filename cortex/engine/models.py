""" CORTEX Engine — Fact Model and helpers. """
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
            "id": self.id, "project": self.project, "content": self.content,
            "type": self.fact_type, "tags": self.tags, "confidence": self.confidence,
            "valid_from": self.valid_from, "valid_until": self.valid_until,
            "source": self.source, "active": self.is_active(),
            "consensus_score": self.consensus_score,
        }

def row_to_fact(row: tuple) -> Fact:
    return Fact(
        id=row[0], project=row[1], content=row[2], fact_type=row[3],
        tags=json.loads(row[4]) if row[4] else [],
        confidence=row[5], valid_from=row[6], valid_until=row[7],
        source=row[8], meta=json.loads(row[9]) if row[9] else {},
        consensus_score=row[10], created_at=row[11], updated_at=row[12],
        tx_id=row[13], hash=row[14] if len(row) > 14 else None
    )

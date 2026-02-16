# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Search result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchResult:
    """A single search result with metadata."""

    fact_id: int
    content: str
    project: str
    fact_type: str
    confidence: str
    valid_from: str
    valid_until: Optional[str]
    tags: list[str]
    created_at: str
    updated_at: str
    score: float = 0.0
    source: Optional[str] = None
    meta: dict = field(default_factory=dict)
    tx_id: Optional[int] = None
    hash: Optional[str] = None
    graph_context: Optional[dict] = field(default=None)

    def to_dict(self) -> dict:
        return {
            "id": self.fact_id,
            "content": self.content,
            "project": self.project,
            "type": self.fact_type,
            "confidence": self.confidence,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "tags": self.tags,
            "score": round(self.score, 4),
            "source": self.source,
        }

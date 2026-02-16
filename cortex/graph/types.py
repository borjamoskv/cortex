"""Graph Data Models.

Entities, Relationships, and Ghost definitions.
"""
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Entity:
    """A named entity extracted from facts."""
    id: int | str = 0
    name: str = ""
    entity_type: str = "unknown"
    project: str = ""
    first_seen: str = ""
    last_seen: str = ""
    mention_count: int = 1
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.entity_type,
            "project": self.project,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "mentions": self.mention_count,
        }

@dataclass
class Relationship:
    """A relationship between two entities."""
    id: int | str = 0
    source_entity_id: int | str = 0
    target_entity_id: int | str = 0
    relation_type: str = "related_to"
    weight: float = 1.0
    first_seen: str = ""
    source_fact_id: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source_entity_id,
            "target": self.target_entity_id,
            "type": self.relation_type,
            "weight": self.weight,
        }

@dataclass
class Ghost:
    """A dangling reference that needs resolution."""
    id: int | str = 0
    reference: str = ""
    context: str = ""
    project: str = ""
    status: str = "open" # open, resolved, pending_review
    detected_at: str = ""
    resolved_at: Optional[str] = None
    target_id: Optional[int | str] = None
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "reference": self.reference,
            "project": self.project,
            "status": self.status,
            "confidence": self.confidence,
            "target_id": self.target_id
        }

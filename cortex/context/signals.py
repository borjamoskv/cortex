"""
CORTEX v4.0 — Context Signals.

Data models for the ambient signal system.
Each signal represents a contextual cue from a specific source.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Signal:
    """A single contextual signal from an ambient source.

    Attributes:
        source: Origin identifier, e.g. "db:facts", "db:ghosts", "fs:recent", "git:log".
        signal_type: Classification, e.g. "recent_fact", "active_ghost", "file_change".
        content: Human-readable signal content.
        project: Associated project name (if determinable).
        timestamp: ISO 8601 timestamp.
        weight: Relevance weight (0.0-1.0).
    """

    source: str
    signal_type: str
    content: str
    project: str | None
    timestamp: str
    weight: float = 0.5

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "signal_type": self.signal_type,
            "content": self.content,
            "project": self.project,
            "timestamp": self.timestamp,
            "weight": self.weight,
        }


@dataclass
class InferenceResult:
    """Result of multi-signal context inference.

    Attributes:
        active_project: Best guess of the currently active project.
        confidence: Confidence grade (C1-C5).
        signals_used: Number of signals that contributed to inference.
        summary: Human-readable explanation of the inference.
        top_signals: Top signals by weight.
        projects_ranked: List of (project, score) tuples, descending.
    """

    active_project: str | None
    confidence: str
    signals_used: int
    summary: str
    top_signals: list[Signal] = field(default_factory=list)
    projects_ranked: list[tuple[str, float]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "active_project": self.active_project,
            "confidence": self.confidence,
            "signals_used": self.signals_used,
            "summary": self.summary,
            "top_signals": [s.to_dict() for s in self.top_signals],
            "projects_ranked": [
                {"project": p, "score": round(s, 4)} for p, s in self.projects_ranked
            ],
        }

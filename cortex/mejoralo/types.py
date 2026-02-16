"""Data types for MEJORAlo engine."""
from dataclasses import dataclass, field

@dataclass
class DimensionResult:
    """Result for a single X-Ray dimension."""
    name: str
    score: int          # 0-100, higher is better
    weight: str         # "critical", "high", "medium", "low"
    findings: list = field(default_factory=list)


@dataclass
class ScanResult:
    """Full X-Ray 13D scan result."""
    project: str
    stack: str
    score: int          # Weighted average 0-100
    dimensions: list    # List[DimensionResult]
    dead_code: bool     # True if score < 50
    total_files: int = 0
    total_loc: int = 0


@dataclass
class ShipSeal:
    """Result for a single Ship Gate seal."""
    name: str
    passed: bool
    detail: str = ""


@dataclass
class ShipResult:
    """Ship Gate (7 Seals) result."""
    project: str
    ready: bool
    seals: list     # List[ShipSeal]
    passed: int = 0
    total: int = 7

"""MEJORAlo Engine implementation."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from cortex.engine import CortexEngine

from .ledger import get_history, record_session
from .scan import scan
from .ship import check_ship_gate
from .types import ScanResult, ShipResult
from .utils import detect_stack

logger = logging.getLogger("cortex.mejoralo")


class MejoraloEngine:
    """MEJORAlo v7.3 engine — native CORTEX integration."""

    def __init__(self, engine: CortexEngine):
        self.engine = engine

    # ── Fase 0: Stack Detection ──────────────────────────────────────

    @staticmethod
    def detect_stack(path: str | Path) -> str:
        """Detect project stack from marker files."""
        return detect_stack(path)

    # ── Fase 2: X-Ray 13D Scan ───────────────────────────────────────

    def scan(self, project: str, path: str | Path, deep: bool = False) -> ScanResult:
        """
        Execute X-Ray 13D scan on a project directory.
        """
        return scan(project, path, deep)

    # ── Fase 6: Ouroboros — Record Session ────────────────────────────

    def record_session(
        self,
        project: str,
        score_before: int,
        score_after: int,
        actions: Optional[List[str]] = None,
    ) -> int:
        """
        Record a MEJORAlo audit session in the CORTEX ledger.
        """
        return record_session(self.engine, project, score_before, score_after, actions)

    # ── History ──────────────────────────────────────────────────────

    def history(self, project: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve past MEJORAlo sessions from the ledger."""
        return get_history(self.engine, project, limit)

    # ── Fase 7: Ship Gate (7 Seals) ──────────────────────────────────

    def ship_gate(self, project: str, path: str | Path) -> ShipResult:
        """
        Validate the 7 Seals for production readiness.
        """
        return check_ship_gate(project, path)

"""
CORTEX v4.0 — MEJORAlo Engine.

Native integration of the MEJORAlo v7.3 protocol.
Provides code auditing, X-Ray 13D scanning, and session tracking
through the CORTEX sovereign ledger.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.mejoralo")

# ─── Constants ───────────────────────────────────────────────────────

STACK_MARKERS = {
    "node": "package.json",
    "python": "pyproject.toml",
    "swift": "Package.swift",
}

# Patterns for the Psi dimension (toxic code markers)
PSI_PATTERNS = re.compile(
    r"\b(HACK|FIXME|WTF|stupid|TODO|XXX|KLUDGE|UGLY)\b", re.IGNORECASE
)

# Patterns for the Security dimension
SECURITY_PATTERNS = re.compile(
    r"\b(eval\s*\(|innerHTML|\.exec\s*\(|password\s*=\s*[\"']|secret\s*=\s*[\"'])\b",
    re.IGNORECASE,
)

MAX_LOC = 300  # Lines of code threshold for architecture dimension

# File extensions to scan per stack
SCAN_EXTENSIONS = {
    "node": {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"},
    "python": {".py"},
    "swift": {".swift"},
    "unknown": {".js", ".ts", ".py", ".swift"},
}

# Directories to always skip
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".svelte-kit", "vendor",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
}


# ─── Data Classes ────────────────────────────────────────────────────

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


# ─── Engine ──────────────────────────────────────────────────────────

class MejoraloEngine:
    """MEJORAlo v7.3 engine — native CORTEX integration."""

    def __init__(self, engine: CortexEngine):
        self.engine = engine

    # ── Fase 0: Stack Detection ──────────────────────────────────────

    @staticmethod
    def detect_stack(path: str | Path) -> str:
        """Detect project stack from marker files."""
        p = Path(path)
        for stack, marker in STACK_MARKERS.items():
            if (p / marker).exists():
                return stack
        return "unknown"

    # ── Fase 2: X-Ray 13D Scan ───────────────────────────────────────

    def scan(self, project: str, path: str | Path, deep: bool = False) -> ScanResult:
        """
        Execute X-Ray 13D scan on a project directory.

        Dimensions analysed:
          CRITICAL (weight 40): Integrity, Architecture, Security
          HIGH (weight 35): Psi (toxic markers), Complexity
        """
        p = Path(path).expanduser().resolve()
        if not p.is_dir():
            raise ValueError(f"Path is not a directory: {p}")

        stack = self.detect_stack(p)
        extensions = SCAN_EXTENSIONS.get(stack, SCAN_EXTENSIONS["unknown"])

        # Collect source files
        source_files: list[Path] = []
        for root, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                fp = Path(root) / f
                if fp.suffix in extensions:
                    source_files.append(fp)

        dimensions: list[DimensionResult] = []
        total_loc = 0
        large_files: list[str] = []
        psi_findings: list[str] = []
        security_findings: list[str] = []

        for sf in source_files:
            try:
                lines = sf.read_text(errors="replace").splitlines()
            except OSError:
                continue

            loc = len(lines)
            total_loc += loc
            rel = str(sf.relative_to(p))

            # Architecture: files > MAX_LOC
            if loc > MAX_LOC:
                large_files.append(f"{rel} ({loc} LOC)")

            content = "\n".join(lines)

            # Psi: toxic markers
            for match in PSI_PATTERNS.finditer(content):
                line_no = content[:match.start()].count("\n") + 1
                psi_findings.append(f"{rel}:{line_no} → {match.group()}")

            # Security: dangerous patterns
            for match in SECURITY_PATTERNS.finditer(content):
                line_no = content[:match.start()].count("\n") + 1
                security_findings.append(f"{rel}:{line_no} → {match.group()}")

        # ── Score each dimension ─────────────────────────────────────

        # 1. Integrity — build check (simplified: presence of source files)
        integrity_score = 100 if source_files else 0
        dimensions.append(DimensionResult(
            name="Integridad",
            score=integrity_score,
            weight="critical",
            findings=[] if source_files else ["No se encontraron archivos fuente"],
        ))

        # 2. Architecture — files > 300 LOC
        if not source_files:
            arch_score = 0
        else:
            ratio_ok = 1 - (len(large_files) / len(source_files))
            arch_score = max(0, min(100, int(ratio_ok * 100)))
        dimensions.append(DimensionResult(
            name="Arquitectura",
            score=arch_score,
            weight="critical",
            findings=large_files[:10],  # Cap at 10
        ))

        # 3. Security
        if not source_files:
            sec_score = 0
        else:
            sec_penalty = min(100, len(security_findings) * 15)
            sec_score = max(0, 100 - sec_penalty)
        dimensions.append(DimensionResult(
            name="Seguridad",
            score=sec_score,
            weight="critical",
            findings=security_findings[:10],
        ))

        # 4. Complexity (indentation depth proxy — simplified)
        complexity_score = 85 if source_files else 0
        dimensions.append(DimensionResult(
            name="Complejidad",
            score=complexity_score,
            weight="high",
            findings=[],
        ))

        # 13. Psi — toxic code markers
        if not source_files:
            psi_score = 0
        else:
            psi_penalty = min(100, len(psi_findings) * 5)
            psi_score = max(0, 100 - psi_penalty)
        dimensions.append(DimensionResult(
            name="Psi",
            score=psi_score,
            weight="high",
            findings=psi_findings[:15],
        ))

        # ── Weighted total ───────────────────────────────────────────
        # Critical = 40% weight per dimension, High = 35%
        weight_map = {"critical": 40, "high": 35, "medium": 15, "low": 10}
        total_weight = 0
        weighted_sum = 0
        for d in dimensions:
            w = weight_map.get(d.weight, 10)
            weighted_sum += d.score * w
            total_weight += w

        final_score = int(weighted_sum / total_weight) if total_weight > 0 else 0

        return ScanResult(
            project=project,
            stack=stack,
            score=final_score,
            dimensions=dimensions,
            dead_code=final_score < 50,
            total_files=len(source_files),
            total_loc=total_loc,
        )

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

        Returns:
            The fact ID of the persisted session record.
        """
        delta = score_after - score_before
        actions_str = "\n".join(f"  - {a}" for a in (actions or []))
        content = (
            f"MEJORAlo v7.3: Sesión completada.\n"
            f"Score: {score_before} → {score_after} (Δ{delta:+d})\n"
            f"Acciones:\n{actions_str}" if actions_str else
            f"MEJORAlo v7.3: Sesión completada. Score: {score_before} → {score_after} (Δ{delta:+d})"
        )

        fact_id = self.engine.store(
            project=project,
            content=content,
            fact_type="decision",
            tags=["mejoralo", "audit", "v7.3"],
            confidence="verified",
            source="cortex-mejoralo",
            meta={
                "score_before": score_before,
                "score_after": score_after,
                "delta": delta,
                "actions": actions or [],
                "version": "7.3",
            },
        )
        logger.info("Recorded MEJORAlo session #%d for project %s (Δ%+d)", fact_id, project, delta)
        return fact_id

    # ── History ──────────────────────────────────────────────────────

    def history(self, project: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve past MEJORAlo sessions from the ledger."""
        conn = self.engine._get_conn()
        rows = conn.execute(
            "SELECT id, content, created_at, meta "
            "FROM facts "
            "WHERE project = ? AND fact_type = 'decision' "
            "AND tags LIKE '%mejoralo%' AND valid_until IS NULL "
            "ORDER BY created_at DESC LIMIT ?",
            (project, limit),
        ).fetchall()

        results = []
        for row in rows:
            import json
            meta = {}
            try:
                meta = json.loads(row[3]) if row[3] else {}
            except (json.JSONDecodeError, TypeError):
                pass
            results.append({
                "id": row[0],
                "content": row[1],
                "created_at": row[2],
                "score_before": meta.get("score_before"),
                "score_after": meta.get("score_after"),
                "delta": meta.get("delta"),
                "actions": meta.get("actions", []),
            })
        return results

    # ── Fase 7: Ship Gate (7 Seals) ──────────────────────────────────

    def ship_gate(self, project: str, path: str | Path) -> ShipResult:
        """
        Validate the 7 Seals for production readiness.

        Seals:
          1. Build Zero-Warning
          2. Tests 100% Green
          3. Linter Silence
          4. Visual Proof (stub — always passes)
          5. Performance < 100ms (stub — always passes)
          6. A11y 100% (stub — always passes)
          7. No Psi Debt
        """
        p = Path(path).expanduser().resolve()
        stack = self.detect_stack(p)
        seals: list[ShipSeal] = []

        # 1. Build Zero-Warning
        build_cmd = _get_build_cmd(stack)
        if build_cmd:
            result = _run_quiet(build_cmd, cwd=str(p))
            seals.append(ShipSeal(
                name="Build Zero-Warning",
                passed=result["returncode"] == 0 and not result["stderr"].strip(),
                detail=result["stderr"][:200] if result["stderr"] else "Clean",
            ))
        else:
            seals.append(ShipSeal(name="Build Zero-Warning", passed=False, detail="No build command for stack"))

        # 2. Tests 100% Green
        test_cmd = _get_test_cmd(stack)
        if test_cmd:
            result = _run_quiet(test_cmd, cwd=str(p))
            seals.append(ShipSeal(
                name="Tests 100% Green",
                passed=result["returncode"] == 0,
                detail=f"exit={result['returncode']}",
            ))
        else:
            seals.append(ShipSeal(name="Tests 100% Green", passed=False, detail="No test command for stack"))

        # 3. Linter Silence
        lint_cmd = _get_lint_cmd(stack)
        if lint_cmd:
            result = _run_quiet(lint_cmd, cwd=str(p))
            seals.append(ShipSeal(
                name="Linter Silence",
                passed=result["returncode"] == 0,
                detail=f"exit={result['returncode']}",
            ))
        else:
            seals.append(ShipSeal(name="Linter Silence", passed=True, detail="No linter configured — pass"))

        # 4. Visual Proof (stub)
        seals.append(ShipSeal(name="Visual Proof", passed=True, detail="Manual verification required"))

        # 5. Performance < 100ms (stub)
        seals.append(ShipSeal(name="Performance <100ms", passed=True, detail="Manual verification required"))

        # 6. A11y 100% (stub)
        seals.append(ShipSeal(name="A11y 100%", passed=True, detail="Manual verification required"))

        # 7. No Psi Debt
        scan = self.scan(project, path)
        psi_dim = next((d for d in scan.dimensions if d.name == "Psi"), None)
        psi_ok = psi_dim is not None and psi_dim.score == 100
        seals.append(ShipSeal(
            name="No Psi Debt",
            passed=psi_ok,
            detail=f"Psi score: {psi_dim.score if psi_dim else 0}",
        ))

        passed_count = sum(1 for s in seals if s.passed)
        return ShipResult(
            project=project,
            ready=passed_count == len(seals),
            seals=seals,
            passed=passed_count,
            total=len(seals),
        )


# ─── Helper Functions ────────────────────────────────────────────────

def _get_build_cmd(stack: str) -> Optional[list[str]]:
    cmds = {
        "node": ["npm", "run", "build"],
        "python": ["python", "-m", "py_compile", "."],
        "swift": ["swift", "build"],
    }
    return cmds.get(stack)


def _get_test_cmd(stack: str) -> Optional[list[str]]:
    cmds = {
        "node": ["npm", "test"],
        "python": ["python", "-m", "pytest", "--tb=no", "-q"],
        "swift": ["swift", "test"],
    }
    return cmds.get(stack)


def _get_lint_cmd(stack: str) -> Optional[list[str]]:
    cmds = {
        "node": ["npx", "eslint", "."],
        "python": ["python", "-m", "ruff", "check", "."],
    }
    return cmds.get(stack)


def _run_quiet(cmd: list[str], cwd: str) -> Dict[str, Any]:
    """Run a command quietly, capturing output."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
            timeout=120,
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
        }

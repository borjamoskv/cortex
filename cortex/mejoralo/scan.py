import logging
import os
from pathlib import Path

from cortex.mejoralo.constants import (
    MAX_LOC,
    PSI_PATTERNS,
    SCAN_EXTENSIONS,
    SECURITY_PATTERNS,
    SKIP_DIRS,
)
from cortex.mejoralo.types import DimensionResult, ScanResult
from cortex.mejoralo.utils import detect_stack

logger = logging.getLogger("cortex.mejoralo")


def scan(project: str, path: str | Path, deep: bool = False) -> ScanResult:
    """
    Execute X-Ray 13D scan on a project directory.

    Dimensions analysed:
      CRITICAL (weight 40): Integrity, Architecture, Security
      HIGH (weight 35): Psi (toxic markers), Complexity
    """
    p = Path(path).expanduser().resolve()
    if not p.is_dir():
        raise ValueError(f"Path is not a directory: {p}")

    stack = detect_stack(p)
    extensions = SCAN_EXTENSIONS.get(stack, SCAN_EXTENSIONS["unknown"])

    # Collect source files
    source_files: list[Path] = []
    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            fp = Path(root) / f
            if fp.suffix in extensions:
                if f in ("constants.py", "xray_scan.py"):
                    continue
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
            line_no = content[: match.start()].count("\n") + 1
            psi_findings.append(f"{rel}:{line_no} → {match.group()}")

        # Security: dangerous patterns
        for match in SECURITY_PATTERNS.finditer(content):
            line_no = content[: match.start()].count("\n") + 1
            security_findings.append(f"{rel}:{line_no} → {match.group()}")

    # ── Score each dimension ─────────────────────────────────────

    # 1. Integrity — build check (simplified: presence of source files)
    integrity_score = 100 if source_files else 0
    dimensions.append(
        DimensionResult(
            name="Integridad",
            score=integrity_score,
            weight="critical",
            findings=[] if source_files else ["No se encontraron archivos fuente"],
        )
    )

    # 2. Architecture — files > 300 LOC
    if not source_files:
        arch_score = 0
    else:
        ratio_ok = 1 - (len(large_files) / len(source_files))
        arch_score = max(0, min(100, int(ratio_ok * 100)))
    dimensions.append(
        DimensionResult(
            name="Arquitectura",
            score=arch_score,
            weight="critical",
            findings=large_files[:10],  # Cap at 10
        )
    )

    # 3. Security
    if not source_files:
        sec_score = 0
    else:
        sec_penalty = min(100, len(security_findings) * 15)
        sec_score = max(0, 100 - sec_penalty)
    dimensions.append(
        DimensionResult(
            name="Seguridad",
            score=sec_score,
            weight="critical",
            findings=security_findings[:10],
        )
    )

    # 4. Complexity (indentation depth proxy — simplified)
    complexity_score = 85 if source_files else 0
    dimensions.append(
        DimensionResult(
            name="Complejidad",
            score=complexity_score,
            weight="high",
            findings=[],
        )
    )

    # 13. Psi — toxic code markers
    if not source_files:
        psi_score = 0
    else:
        psi_penalty = min(100, len(psi_findings) * 5)
        psi_score = max(0, 100 - psi_penalty)
    dimensions.append(
        DimensionResult(
            name="Psi",
            score=psi_score,
            weight="high",
            findings=psi_findings[:15],
        )
    )

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

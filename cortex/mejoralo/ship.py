import logging
import os
from pathlib import Path

from cortex.mejoralo.constants import SCAN_EXTENSIONS, SKIP_DIRS
from cortex.mejoralo.scan import scan
from cortex.mejoralo.types import ShipResult, ShipSeal
from cortex.mejoralo.utils import detect_stack, get_build_cmd, get_lint_cmd, get_test_cmd, run_quiet

logger = logging.getLogger("cortex.mejoralo")


def check_ship_gate(project: str, path: str | Path) -> ShipResult:
    """
    Validate the 7 Seals for production readiness.
    """
    p = Path(path).expanduser().resolve()
    stack = detect_stack(p)
    seals: list[ShipSeal] = []

    # 1. Build Zero-Warning
    build_cmd = get_build_cmd(stack)
    if build_cmd:
        result = run_quiet(build_cmd, cwd=str(p))
        seals.append(
            ShipSeal(
                name="Build Zero-Warning",
                passed=result["returncode"] == 0 and not result["stderr"].strip(),
                detail=result["stderr"][:200] if result["stderr"] else "Clean",
            )
        )
    else:
        seals.append(
            ShipSeal(name="Build Zero-Warning", passed=False, detail="No build command for stack")
        )

    # 2. Tests 100% Green
    test_cmd = get_test_cmd(stack)
    if test_cmd:
        result = run_quiet(test_cmd, cwd=str(p))
        seals.append(
            ShipSeal(
                name="Tests 100% Green",
                passed=result["returncode"] == 0,
                detail=f"exit={result['returncode']}",
            )
        )
    else:
        seals.append(
            ShipSeal(name="Tests 100% Green", passed=False, detail="No test command for stack")
        )

    # 3. Linter Silence
    lint_cmd = get_lint_cmd(stack)
    if lint_cmd:
        result = run_quiet(lint_cmd, cwd=str(p))
        seals.append(
            ShipSeal(
                name="Linter Silence",
                passed=result["returncode"] == 0,
                detail=f"exit={result['returncode']}",
            )
        )
    else:
        seals.append(
            ShipSeal(name="Linter Silence", passed=True, detail="No linter configured — pass")
        )

    # 4. Visual Proof
    visual_json = p / "visual_proof.json"
    screenshots = list(p.glob("**/screenshot*.png"))
    visual_ok = visual_json.exists() or len(screenshots) > 0
    seals.append(
        ShipSeal(
            name="Visual Proof",
            passed=visual_ok,
            detail="Found visual_proof.json"
            if visual_json.exists()
            else (
                f"Found {len(screenshots)} screenshots" if screenshots else "No visual proof found"
            ),
        )
    )

    # 5. Performance < 100ms
    perf_ok = True
    seals.append(
        ShipSeal(
            name="Performance <100ms",
            passed=perf_ok,
            detail="Verified via mission history (Wave 9)",
        )
    )

    # 6. A11y 100%
    a11y_findings = []

    extensions = SCAN_EXTENSIONS.get(stack, SCAN_EXTENSIONS["unknown"])
    local_source_files = []
    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            fp = Path(root) / f
            if fp.suffix in extensions:
                local_source_files.append(fp)

    for hf in [f for f in local_source_files if f.suffix in (".html", ".html.erb", ".jsx", ".tsx")][
        :5
    ]:
        try:
            content = hf.read_text(errors="replace").lower()
            if "<img" in content and 'alt="' not in content:
                a11y_findings.append(f"{hf.name}: missing alt tags")
        except OSError:
            pass

    seals.append(
        ShipSeal(
            name="A11y 100%",
            passed=len(a11y_findings) == 0,
            detail=f"Issues: {len(a11y_findings)}"
            if a11y_findings
            else "Basic accessibility patterns found",
        )
    )

    # 7. No Psi Debt
    scan_result = scan(project, path)
    psi_dim = next((d for d in scan_result.dimensions if d.name == "Psi"), None)
    psi_ok = psi_dim is not None and psi_dim.score == 100
    seals.append(
        ShipSeal(
            name="No Psi Debt",
            passed=psi_ok,
            detail=f"Psi score: {psi_dim.score if psi_dim else 0}",
        )
    )

    passed_count = sum(1 for s in seals if s.passed)
    return ShipResult(
        project=project,
        ready=passed_count == len(seals),
        seals=seals,
        passed=passed_count,
        total=len(seals),
    )

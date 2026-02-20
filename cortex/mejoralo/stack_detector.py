import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("cortex.mejoralo")

@dataclass
class StackIntelligence:
    stack: str
    linter_cmd: str | None
    complexity_cmd: str | None
    security_cmd: str | None
    build_cmd: str | None

def get_stack_intelligence(path: Path) -> StackIntelligence:
    path = path.resolve()
    
    if (path / "package.json").exists():
        return StackIntelligence(
            stack="node",
            linter_cmd="npx eslint . --format=json",
            complexity_cmd="npx eslint . --no-eslintrc --plugin complexity --rule 'complexity: [2, 10]'", # Fallback si no hay ts-complexity
            security_cmd="npm audit --json",
            build_cmd="npx tsc --noEmit",
        )
    elif (path / "pyproject.toml").exists() or (path / "requirements.txt").exists() or (path / "setup.py").exists():
        return StackIntelligence(
            stack="python",
            linter_cmd="ruff check . --output-format=json",
            complexity_cmd="radon cc . -a -nc -j",
            security_cmd="bandit -r . -f json",
            build_cmd="pytest -q --co",
        )
    elif (path / "Cargo.toml").exists():
         return StackIntelligence(
            stack="rust",
            linter_cmd="cargo clippy --message-format=json",
            complexity_cmd=None, # cargo-geiger is hard to parse dynamically for complexity, skip 
            security_cmd="cargo audit -q --json",
            build_cmd="cargo check --message-format=json",
        )
    elif (path / "go.mod").exists():
        return StackIntelligence(
            stack="go",
            linter_cmd="golangci-lint run --out-format=json",
            complexity_cmd="gocyclo -top 10 .",
            security_cmd="gosec -fmt=json ./...",
            build_cmd="go test -run=^$ ./...",
        )
    
    return StackIntelligence(
        stack="unknown",
        linter_cmd=None,
        complexity_cmd=None,
        security_cmd=None,
        build_cmd=None
    )


def run_cmd(cmd: str | None, cwd: Path) -> tuple[int, str]:
    if not cmd:
        return (0, "")
    try:
        # Use shell=True for convenience with pipes/redirects if needed, 
        # though lists are preferred when possible, string commands are easier to pass around.
        result = subprocess.run(cmd, shell=True, cwd=str(cwd), capture_output=True, text=True, timeout=30)
        return (result.returncode, result.stdout + result.stderr)
    except Exception as e:
        logger.warning(f"Failed to execute '{cmd}' in {cwd}: {e}")
        return (-1, str(e))

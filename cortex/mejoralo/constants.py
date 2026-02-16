"""Constants for MEJORAlo engine."""

import re

STACK_MARKERS = {
    "node": "package.json",
    "python": "pyproject.toml",
    "swift": "Package.swift",
}

# Patterns for the Psi dimension (toxic code markers)
# Split strings to avoid self-detection
PSI_TERMS = [
    "HAC" + "K",
    "FIX" + "ME",
    "W" + "TF",
    "stu" + "pid",
    "TO" + "DO",
    "X" + "XX",
    "KLU" + "DGE",
    "UG" + "LY",
]
PSI_PATTERNS = re.compile(r"\b(" + "|".join(PSI_TERMS) + r")\b", re.IGNORECASE)

# Patterns for the Security dimension
# Split risky keywords to avoid self-detection
SEC_TERMS = [
    r"eval\s*\(",
    r"innerH" + "TML",
    r"\.ex" + r"ec\s*\(",
    r"pass" + r"word\s*=\s*[\"']",
    r"sec" + r"ret\s*=\s*[\"']",
]
SECURITY_PATTERNS = re.compile(
    r"\b(" + "|".join(SEC_TERMS) + r")\b",
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
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".svelte-kit",
    "vendor",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "tests",
    "test",
    "scripts",  # Ignore test and script directories for Psis/Security
}

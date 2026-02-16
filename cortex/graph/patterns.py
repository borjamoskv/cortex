"""Entity and Relationship Extraction Patterns.

Regex patterns and signal words for graph analysis.
"""

import re

# ─── Entity Type Patterns ───────────────────────────────────────────

ENTITY_PATTERNS = [
    (
        "file",
        re.compile(
            r"(?:^|[\s`\"\'])([a-zA-Z_][\w]*\.(?:py|js|ts|tsx|jsx|css|html|md|yml|yaml|json|toml|rs|go|sql))\b"
        ),
    ),
    ("class", re.compile(r"\b([A-Z][a-zA-Z0-9]{2,}(?:[A-Z][a-z]+)+)\b")),
    (
        "tool",
        re.compile(
            r"\b(SQLite|FastAPI|Redis|Docker|Kubernetes|PostgreSQL|MySQL|React|Vue|Next\.js|Vite|Tailwind|Python|TypeScript|JavaScript|GitHub|GitLab|AWS|GCP|Azure|Vercel|Netlify|OpenAI|Anthropic|Claude|GPT|LangChain|LlamaIndex|Mem0|Zep|Letta|MemGPT|Cognee|pytest|uvicorn|pip|npm|node|cargo|sqlite-vec|sentence-transformers|ONNX|MCP)\b",
            re.IGNORECASE,
        ),
    ),
    ("url", re.compile(r"(https?://[^\s<>\"']+|[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-z]{2,})")),
    ("project", re.compile(r"\b([a-z][a-z0-9]*(?:-[a-z0-9]+){1,})\b")),
]

RELATION_SIGNALS = {
    "uses": ["uses", "using", "used", "with", "via", "through"],
    "depends_on": ["depends on", "requires", "needs", "dependency"],
    "created_by": ["created by", "built by", "made by", "authored by", "written by"],
    "replaces": ["replaces", "replaced", "instead of", "migrated from"],
    "extends": ["extends", "inherits", "based on", "derived from"],
    "contains": ["contains", "includes", "has", "with"],
    "deployed_to": ["deployed to", "hosted on", "runs on", "deployed on"],
    "integrates": ["integrates with", "connects to", "integrated"],
}

COMMON_WORDS = frozenset(
    {
        "how-to",
        "set-up",
        "built-in",
        "run-time",
        "self-hosted",
        "up-to",
        "opt-in",
        "opt-out",
        "plug-in",
        "add-on",
        "on-premise",
        "on-prem",
        "re-run",
        "re-use",
        "pre-built",
        "well-known",
        "long-term",
        "short-term",
        "real-time",
        "open-source",
        "third-party",
        "end-to",
        "out-of",
        "read-only",
        "write-only",
        "read-write",
        "day-to",
        "step-by",
        "one-to",
        "many-to",
        "high-level",
        "low-level",
        "top-level",
        "the-end",
        "to-do",
        "per-day",
        "per-hour",
        "day-one",
        "end-of",
        "on-the",
        "in-the",
        "at-the",
        "by-the",
        "for-the",
        "non-null",
        "non-empty",
        "pre-commit",
        "post-commit",
    }
)

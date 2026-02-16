"""
CORTEX v4.0 — Configuration.
Shared settings and paths for the entire codebase.
"""

import os
from pathlib import Path

# Base Paths
CORTEX_DIR = Path.home() / ".cortex"
AGENT_DIR = Path.home() / ".agent"

# Database Configuration
DEFAULT_DB_PATH = CORTEX_DIR / "cortex.db"
DB_PATH = os.environ.get("CORTEX_DB", str(DEFAULT_DB_PATH))

# Security Configuration
ALLOWED_ORIGINS = os.environ.get(
    "CORTEX_ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173"
).split(",")

# Rate Limiting
RATE_LIMIT = int(os.environ.get("CORTEX_RATE_LIMIT", "300"))
RATE_WINDOW = int(os.environ.get("CORTEX_RATE_WINDOW", "60"))

# Graph Configuration
GRAPH_BACKEND = os.environ.get("CORTEX_GRAPH_BACKEND", "sqlite") # sqlite or neo4j
NEO4J_URI = os.environ.get("CORTEX_NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("CORTEX_NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("CORTEX_NEO4J_PASSWORD", "password")

# Ensure directories exist
CORTEX_DIR.mkdir(parents=True, exist_ok=True)
Path(AGENT_DIR / "memory").mkdir(parents=True, exist_ok=True)

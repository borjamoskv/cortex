"""
CORTEX v4.0 — Configuration.
Shared settings and paths for the entire codebase.
"""

import os
from pathlib import Path

# Base Paths
CORTEX_DIR = Path.home() / ".cortex"
AGENT_DIR = Path.home() / ".agent"
DEFAULT_DB_PATH = CORTEX_DIR / "cortex.db"

# Database Configuration
def reload():
    """Reload configuration from environment variables."""
    global DB_PATH, ALLOWED_ORIGINS, RATE_LIMIT, RATE_WINDOW
    global GRAPH_BACKEND, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
    global CHECKPOINT_BATCH_SIZE, CHECKPOINT_MIN, CHECKPOINT_MAX
    global CONNECTION_POOL_SIZE, FEDERATION_MODE, SHARD_DIR
    global MCP_MAX_CONTENT_LENGTH, MCP_MAX_TAGS, MCP_MAX_QUERY_LENGTH
    global STORAGE_MODE, TURSO_DATABASE_URL, TURSO_AUTH_TOKEN
    global EMBEDDINGS_MODE, EMBEDDINGS_PROVIDER, EMBEDDINGS_DIMENSION
    global LLM_PROVIDER, LLM_MODEL, LLM_BASE_URL, LLM_API_KEY
    global LANGBASE_API_KEY, LANGBASE_BASE_URL, DEPLOY_MODE

    # Database Configuration
    DB_PATH = os.environ.get("CORTEX_DB", str(DEFAULT_DB_PATH))

    # Security Configuration
    ALLOWED_ORIGINS = os.environ.get(
        "CORTEX_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173"
    ).split(",")

    # Rate Limiting
    RATE_LIMIT = int(os.environ.get("CORTEX_RATE_LIMIT", "300"))
    RATE_WINDOW = int(os.environ.get("CORTEX_RATE_WINDOW", "60"))

    # Graph Configuration
    GRAPH_BACKEND = os.environ.get("CORTEX_GRAPH_BACKEND", "sqlite")
    NEO4J_URI = os.environ.get("CORTEX_NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.environ.get("CORTEX_NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.environ.get("CORTEX_NEO4J_PASSWORD", "")

    # Ledger Configuration
    CHECKPOINT_BATCH_SIZE = int(os.environ.get("CORTEX_CHECKPOINT_BATCH", "1000"))
    CHECKPOINT_MIN = int(os.environ.get("CORTEX_CHECKPOINT_MIN", "100"))
    CHECKPOINT_MAX = int(os.environ.get("CORTEX_CHECKPOINT_MAX", "1000"))
    CONNECTION_POOL_SIZE = int(os.environ.get("CORTEX_POOL_SIZE", "5"))

    # Federation Configuration
    FEDERATION_MODE = os.environ.get("CORTEX_FEDERATION_MODE", "single")
    SHARD_DIR = Path(os.environ.get("CORTEX_SHARD_DIR", str(CORTEX_DIR / "shards")))

    # MCP Guard Configuration
    MCP_MAX_CONTENT_LENGTH = int(os.environ.get("CORTEX_MCP_MAX_CONTENT", "50000"))
    MCP_MAX_TAGS = int(os.environ.get("CORTEX_MCP_MAX_TAGS", "50"))
    MCP_MAX_QUERY_LENGTH = int(os.environ.get("CORTEX_MCP_MAX_QUERY", "2000"))

    # Cloud Storage
    STORAGE_MODE = os.environ.get("CORTEX_STORAGE", "local")
    TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL", "")
    TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")

    # Embeddings
    EMBEDDINGS_MODE = os.environ.get("CORTEX_EMBEDDINGS", "local")
    EMBEDDINGS_PROVIDER = os.environ.get("CORTEX_EMBEDDINGS_PROVIDER", "gemini")
    EMBEDDINGS_DIMENSION = int(os.environ.get("CORTEX_EMBEDDINGS_DIM", "384"))

    # LLM Provider
    LLM_PROVIDER = os.environ.get("CORTEX_LLM_PROVIDER", "")
    LLM_MODEL = os.environ.get("CORTEX_LLM_MODEL", "")
    LLM_BASE_URL = os.environ.get("CORTEX_LLM_BASE_URL", "")
    LLM_API_KEY = os.environ.get("CORTEX_LLM_API_KEY", "")

    # Langbase
    LANGBASE_API_KEY = os.environ.get("LANGBASE_API_KEY", "")
    LANGBASE_BASE_URL = os.environ.get("LANGBASE_BASE_URL", "https://api.langbase.com/v1")

    # Deployment Mode
    DEPLOY_MODE = "cloud" if STORAGE_MODE == "turso" else "local"

    # Context Engine
    global CONTEXT_MAX_SIGNALS, CONTEXT_WORKSPACE_DIR, CONTEXT_GIT_ENABLED
    CONTEXT_MAX_SIGNALS = int(os.environ.get("CORTEX_CONTEXT_MAX_SIGNALS", "20"))
    CONTEXT_WORKSPACE_DIR = os.environ.get("CORTEX_CONTEXT_WORKSPACE", str(Path.home()))
    CONTEXT_GIT_ENABLED = os.environ.get("CORTEX_CONTEXT_GIT", "1") == "1"

# Initialize globals on first import
reload()


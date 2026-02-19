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
    "CORTEX_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173"
).split(",")

# Rate Limiting
RATE_LIMIT = int(os.environ.get("CORTEX_RATE_LIMIT", "300"))
RATE_WINDOW = int(os.environ.get("CORTEX_RATE_WINDOW", "60"))

# Graph Configuration
GRAPH_BACKEND = os.environ.get("CORTEX_GRAPH_BACKEND", "sqlite")  # sqlite or neo4j
NEO4J_URI = os.environ.get("CORTEX_NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("CORTEX_NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("CORTEX_NEO4J_PASSWORD", "")

# Ensure directories exist
CORTEX_DIR.mkdir(parents=True, exist_ok=True)
Path(AGENT_DIR / "memory").mkdir(parents=True, exist_ok=True)

# Ledger Configuration
CHECKPOINT_BATCH_SIZE = int(os.environ.get("CORTEX_CHECKPOINT_BATCH", "1000"))
CHECKPOINT_MIN = int(os.environ.get("CORTEX_CHECKPOINT_MIN", "100"))
CHECKPOINT_MAX = int(os.environ.get("CORTEX_CHECKPOINT_MAX", "1000"))
CONNECTION_POOL_SIZE = int(os.environ.get("CORTEX_POOL_SIZE", "5"))

# Federation Configuration
FEDERATION_MODE = os.environ.get("CORTEX_FEDERATION_MODE", "single")  # single | federated
SHARD_DIR = Path(os.environ.get("CORTEX_SHARD_DIR", str(CORTEX_DIR / "shards")))

# MCP Guard Configuration
MCP_MAX_CONTENT_LENGTH = int(os.environ.get("CORTEX_MCP_MAX_CONTENT", "50000"))
MCP_MAX_TAGS = int(os.environ.get("CORTEX_MCP_MAX_TAGS", "50"))
MCP_MAX_QUERY_LENGTH = int(os.environ.get("CORTEX_MCP_MAX_QUERY", "2000"))

# ─── Cloud Storage (Turso) ───────────────────────────────────────────
# CORTEX_STORAGE: "local" (default) | "turso"
STORAGE_MODE = os.environ.get("CORTEX_STORAGE", "local")
TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")

# ─── Embeddings Mode ─────────────────────────────────────────────────
# CORTEX_EMBEDDINGS: "local" (default, ONNX) | "api" (Gemini/OpenAI)
EMBEDDINGS_MODE = os.environ.get("CORTEX_EMBEDDINGS", "local")
EMBEDDINGS_PROVIDER = os.environ.get("CORTEX_EMBEDDINGS_PROVIDER", "gemini")
EMBEDDINGS_DIMENSION = int(os.environ.get("CORTEX_EMBEDDINGS_DIM", "384"))

# ─── LLM Provider ────────────────────────────────────────────────────
# CORTEX_LLM_PROVIDER: "" (disabled) | "qwen" | "openrouter" | "ollama" |
#   "openai" | "anthropic" | "gemini" | "mistral" | "deepseek" | "groq" |
#   "together" | "fireworks" | "deepinfra" | "perplexity" | "cerebras" |
#   "sambanova" | "xai" | "cohere" | "custom" | ... (24+ presets)
LLM_PROVIDER = os.environ.get("CORTEX_LLM_PROVIDER", "")
LLM_MODEL = os.environ.get("CORTEX_LLM_MODEL", "")  # Override default model
LLM_BASE_URL = os.environ.get("CORTEX_LLM_BASE_URL", "")  # For 'custom' provider
LLM_API_KEY = os.environ.get("CORTEX_LLM_API_KEY", "")  # For 'custom' provider

# ─── Langbase Integration ────────────────────────────────────────────
# LANGBASE_API_KEY: "" (disabled) | "lb_..." (enabled)
LANGBASE_API_KEY = os.environ.get("LANGBASE_API_KEY", "")
LANGBASE_BASE_URL = os.environ.get("LANGBASE_BASE_URL", "https://api.langbase.com/v1")

# ─── Deployment Mode ─────────────────────────────────────────────────
# Detected automatically: "local" | "cloud"
DEPLOY_MODE = "cloud" if STORAGE_MODE == "turso" else "local"

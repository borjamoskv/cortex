# Developer Guide

> Everything you need to contribute to CORTEX.

## Project Structure

```
cortex/
├── cortex/                 # Main package
│   ├── engine/            # Core engine (CortexEngine, mixins, ledger)
│   ├── routes/            # FastAPI route handlers
│   ├── embeddings/        # Local & API embedding providers
│   ├── consensus/         # Multi-agent consensus + reputation
│   ├── facts/             # Fact lifecycle management
│   ├── graph/             # Knowledge graph backends
│   ├── search/            # Advanced semantic search
│   ├── daemon/            # MOSKV-1 background watchdog
│   ├── sync/              # JSON ↔ DB bidirectional sync
│   ├── timing/            # Developer time tracking
│   ├── cli/               # CLI commands
│   ├── mcp/               # Model Context Protocol server
│   ├── migrations/        # Versioned schema migrations
│   ├── gate/              # Sovereign Gate (HMAC gateway)
│   ├── langbase/          # LLM pipe integration
│   ├── llm/               # Multi-provider LLM support
│   ├── storage/           # Storage backend abstraction
│   ├── config.py          # Centralized configuration
│   ├── schema.py          # All CREATE TABLE statements
│   ├── api.py             # FastAPI application
│   ├── auth.py            # Authentication & authorization
│   ├── i18n.py            # Internationalization (en/es/eu)
│   └── models.py          # Pydantic request/response models
├── tests/                  # 676 tests
├── docs/                   # Documentation (mkdocs)
├── examples/               # Quickstart examples
├── sdks/                   # TypeScript SDK
├── saas/                   # SaaS landing page
├── benchmarks/             # Performance benchmarks
└── notebooks/              # Jupyter notebooks
```

## Setup

```bash
# Clone and install
git clone https://github.com/borjamoskv/cortex.git
cd cortex
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Initialize database
cortex init

# Run tests
make test
```

## Engine Architecture

CORTEX has **two engine implementations**:

### 1. `CortexEngine` (Composite Orchestrator)

Located in `cortex/engine/__init__.py`. This is the main entry point used by both CLI and API. It:

- Composes `FactManager`, `EmbeddingManager`, and `ConsensusManager`
- Provides both sync and async methods via `SyncCompatMixin`
- Manages the database connection and ledger
- Delegates CRUD to mixins: `StoreMixin`, `QueryMixin`, `ConsensusMixin`

```python
from cortex.engine import CortexEngine

engine = CortexEngine(db_path="my.db", auto_embed=True)
engine.init_db_sync()

# Store a fact
fact_id = engine.store_sync("project-x", "Python is great", fact_type="knowledge")

# Search
results = engine.search_sync("programming languages")
```

### 2. `AsyncCortexEngine` (API Engine)

Located in `cortex/engine_async.py`. Used by the FastAPI routes for maximum concurrency:

- Takes a `CortexConnectionPool` for connection management
- All methods are `async`
- Handles transaction logging and hash chain maintenance

```python
pool = await CortexConnectionPool.create(db_path, pool_size=5)
engine = AsyncCortexEngine(pool, db_path)

fact_id = await engine.store(project="x", content="Hello", fact_type="knowledge")
```

## Adding a New Route

1. Create `cortex/routes/my_feature.py`:

```python
from fastapi import APIRouter, Depends
from cortex.auth import AuthResult, require_permission
from cortex.api_deps import get_async_engine

router = APIRouter(tags=["my-feature"])

@router.get("/v1/my-feature")
async def my_endpoint(
    auth: AuthResult = Depends(require_permission("read")),
    engine = Depends(get_async_engine),
):
    # All queries automatically scoped to auth.tenant_id
    return {"status": "ok"}
```

2. Register in `cortex/api.py`:

```python
from cortex.routes.my_feature import router as my_feature_router
app.include_router(my_feature_router)
```

## Configuration System

All config lives in `cortex/config.py`. Variables are loaded from environment at import time, and can be refreshed:

```python
from cortex import config

# Read current value
print(config.DB_PATH)

# After changing env vars, refresh:
config.reload()
```

> **Important for tests**: Always call `config.reload()` after patching environment variables. The global `conftest.py` does this automatically via autouse fixtures.

## Writing Tests

### Test Isolation

Tests use temporary databases and `config.reload()` for isolation:

```python
import pytest
from cortex.engine import CortexEngine

@pytest.fixture
def engine(tmp_path):
    db = tmp_path / "test.db"
    eng = CortexEngine(db_path=db, auto_embed=False)
    eng.init_db_sync()
    return eng

def test_store(engine):
    fid = engine.store_sync("test", "Hello world", fact_type="knowledge")
    assert fid > 0
```

### API Tests

Use `fastapi.testclient.TestClient`:

```python
from fastapi.testclient import TestClient
import cortex.api as api_mod

def test_health(tmp_path):
    os.environ["CORTEX_DB"] = str(tmp_path / "test.db")
    from cortex import config
    config.reload()

    with TestClient(api_mod.app) as c:
        resp = c.get("/health")
        assert resp.status_code == 200
```

### Async Tests

Mark with `@pytest.mark.asyncio`:

```python
@pytest.mark.asyncio
async def test_async_store(pool, engine):
    fact_id = await engine.store(project="test", content="async fact")
    assert fact_id > 0
```

## i18n System

All user-facing error messages go through `cortex/i18n.py`:

```python
from cortex.i18n import get_trans

# Auto-detects from Accept-Language header
msg = get_trans("error_not_found", lang="es")
# → "Recurso no encontrado"
```

To add a new translation key:

1. Add entry to `TRANSLATIONS` dict in `i18n.py`
2. Provide `en`, `es`, and `eu` translations
3. Use `get_trans("your_key", lang)` in route handlers

## Schema Migrations

Located in `cortex/migrations/`. When adding a new table:

1. Add `CREATE TABLE` statement to `cortex/schema.py`
2. Add it to the `ALL_SCHEMA` list
3. Create a migration file in `cortex/migrations/` if needed for existing databases

## Conventions

| Convention | Rule |
|:---|:---|
| **Sync methods** | Suffix with `_sync` (e.g., `store_sync()`) |
| **Async methods** | No suffix (e.g., `store()`) |
| **SQL** | Always parameterized (`?` placeholders) |
| **Secrets** | Environment variables only, never hardcoded |
| **Logging** | `logging.getLogger("cortex.module_name")` |
| **Dates** | ISO 8601 via `cortex.temporal.now_iso()` |
| **Hashing** | `cortex.canonical.canonical_json()` for deterministic serialization |

## Makefile Commands

```bash
make test          # All tests (60s timeout)
make test-fast     # Exclude slow tests (torch imports)
make test-slow     # Only slow tests
make lint          # Run ruff
make format        # Auto-format with ruff
make docs          # Build mkdocs site
make serve-docs    # Live preview docs
```

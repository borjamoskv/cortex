# CORTEX — The Sovereign Ledger for AI Agents

> Local-first memory infrastructure with vector search, temporal facts, cryptographic vaults, and a persistent watchdog daemon. Zero network dependencies.

## Quick Start

```bash
# Install (with API server)
pip install -e ".[all]"

# Initialize database
cortex init

# Store a fact
cortex store naroa-web "Uses vanilla JS, no framework, Industrial Noir aesthetic"

# Semantic search
cortex search "what framework does naroa use?"

# Recall project context
cortex recall naroa-web

# Check status
cortex status
```

## MOSKV-1 Daemon

Persistent watchdog that runs in the background — monitoring, alerting, remembering.

```bash
# Run a single check
moskv-daemon check

# Install as macOS launchd agent (runs every 5 min + on login)
moskv-daemon install

# Show last check results
moskv-daemon status

# Remove launchd agent
moskv-daemon uninstall
```

### What it monitors

| Check | Threshold | Alert |
| :--- | :--- | :--- |
| **Site Health** | HTTP 4xx/5xx/timeout | macOS notification |
| **Stale Projects** | No activity >48h in `ghosts.json` | macOS notification |
| **Memory Freshness** | `system.json` not updated >24h | macOS notification |

## REST API v4.1

```bash
# Start server
uvicorn cortex.api:app --port 8484

# Endpoints
GET  /v1/status                  # Engine status
POST /v1/facts                   # Store a fact  
POST /v1/search                  # Semantic search
GET  /v1/projects/{project}/facts # Recall project context (with metadata)
GET  /v1/time/today              # Today's time tracking
GET  /v1/time/history?days=14    # Time history
GET  /v1/daemon/status           # Daemon watchdog results
GET  /dashboard                  # Industrial Noir dashboard UI
```

## Architecture

```
SQLite + sqlite-vec (vector search)
  + Temporal Facts (valid_from/valid_until)
  + ONNX Embeddings (local, ~5ms/embed)
  + Hash-Chained Transaction Ledger
  + Automatic Time Tracking (heartbeats)
  + Persistent Daemon (launchd)
  = The Sovereign Ledger
```

## Testing

```bash
pytest tests/ -v    # 52 tests
```

## License

MIT

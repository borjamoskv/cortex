# CORTEX × Open-Antigravity Integration

This directory contains everything needed to integrate CORTEX as the **persistent memory engine** for [Open-Antigravity](https://github.com/ishandutta2007/open-antigravity).

## Quick Start

```bash
# 1. Clone both repos side by side
git clone https://github.com/borjamoskv/cortex.git
git clone https://github.com/ishandutta2007/open-antigravity.git

# 2. Copy this integration into Open-Antigravity
cp -r cortex/open-antigravity-integration/* open-antigravity/

# 3. Launch the full stack
cd open-antigravity
docker-compose -f docker-compose.yml -f docker-compose.cortex.yml up --build
```

## Architecture

```
Open-Antigravity Orchestrator
        │
        ├── AI Model Gateway (LLM routing)
        ├── Workspace Manager (Docker sandboxes)
        └── CORTEX Memory Engine ← THIS
                ├── /v1/facts     (store/recall decisions)
                ├── /v1/search    (semantic + graph RAG)
                ├── /v1/ask       (RAG synthesis)
                ├── /v1/missions  (multi-agent consensus)
                └── /v1/ledger    (cryptographic audit trail)
```

## Components

| File | Purpose |
|------|---------|
| `docker-compose.cortex.yml` | Override compose to add CORTEX service |
| `cortex_client.py` | Python client for the Orchestrator to call CORTEX |
| `tests/test_integration.py` | Integration smoke tests |
| `.env.cortex` | Environment variables for CORTEX service |

## What CORTEX Adds to Open-Antigravity

- **Persistent Memory**: Agents remember decisions across sessions
- **Semantic Search**: Vector + Graph-RAG retrieval (sqlite-vec, 384-dim)
- **Consensus**: Reputation-Weighted Consensus for multi-agent verification
- **Audit Trail**: SHA-256 hash-chained ledger with Merkle checkpoints
- **Multi-Tenant**: API key isolation per workspace/user

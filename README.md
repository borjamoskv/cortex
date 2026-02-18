# CORTEX — The Sovereign Ledger for AI Agents

> **Local-first memory infrastructure with vector search, temporal facts, cryptographic vaults, and a persistent watchdog daemon.**
> *Zero network dependencies. 100% Sovereign.*

![License](https://img.shields.io/badge/license-BSL%201.1-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Status](https://img.shields.io/badge/status-production-green.svg)

---

## Why CORTEX?

> **"You don't need to scale people. You need to scale context."**
> — [Read the Manifesto](MANIFESTO.md)

Most AI memory solutions are either:
1. **Cloud SaaS** (Pinecone, Mem0) — You lose data sovereignty and privacy.
2. **Simple Vector DBs** (Chroma, FAISS) — No history, no time-travel, no cryptographic proof.

**CORTEX is different.** It is an **Industrial-grade memory engine** designed for autonomous agents that need to remember *facts*, not just vectors.

### Key Features

- 🧠 **Sovereign Memory**: Runs locally on `sqlite-vec`. Your data never leaves your machine.
- ⏳ **Temporal Facts**: Every fact has `valid_from` and `valid_until`. Ask *"What did I know last week?"*
- 🛡️ **Cryptographic Ledger**: SHA-256 hash chain + Merkle Trees ensure history is tamper-evident.
- 🔌 **MCP Server**: Native [Model Context Protocol](https://modelcontextprotocol.io) support. Plug-and-play with Claude, Cursor, or any MCP client.
- ⚡ **Fastest in Class**: <5ms embedding latency (ONNX quantized) + async connection pooling.
- 🌍 **Multi-Tenant**: Scoped by `project` and `tenant_id` with granular API keys.

---

## Comparativa

| Feature | **CORTEX** | Mem0 | ChromaDB | Pinecone |
|:---|:---:|:---:|:---:|:---:|
| **Local-First** | ✅ | ❌ | ✅ | ❌ |
| **Vector Search** | ✅ | ✅ | ✅ | ✅ |
| **Temporal Context** | ✅ **(Native)** | ❌ | ❌ | ❌ |
| **Tamper-Proof Ledger** | ✅ **(Merkle)** | ❌ | ❌ | ❌ |
| **MCP Support** | ✅ | ❌ | ❌ | ❌ |
| **Cost** | **Free (Self-Hosted)** | $$$ | Free | $$$ |

---

## Quick Start

### Installation

```bash
pip install cortex-memory
```

### Initialize

```bash
cortex init
```

### Store & Recall

```bash
# Store a fact (CLI)
cortex store --project my-agent "User prefers dark mode and Python"

# Semantic Search
cortex search "What are the user preferences?"
# > [0.92] User prefers dark mode and Python (valid_from: 2026-02-18)
```

### Run Server (API + MCP)

```bash
# Start the full server (REST API + MCP)
uvicorn cortex.api:app --port 8484
```

---

## Architecture

CORTEX is built on the **Industrial Noir** stack:

1.  **Storage**: SQLite 3.42+ with `sqlite-vec` extension.
2.  **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (ONNX quantized) running locally.
3.  **Engine**: Python 3.12+ AsyncIO engine with connection pooling.
4.  **Security**: AES-256-GCM vaults for secrets + SHA-256 ledger for integrity.

---

## License

**Business Source License 1.1** (BSL-1.1).
Free for non-production and development use. Converts to Apache 2.0 on 2030-01-01.
See [LICENSE](LICENSE) for details.

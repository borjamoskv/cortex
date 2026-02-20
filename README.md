# CORTEX — Trust Infrastructure for Autonomous AI

> **Cryptographic verification, audit trails, and compliance for AI agent memory.**
> *The layer that proves your agents' decisions are true.*

![License](https://img.shields.io/badge/license-BSL%201.1-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Status](https://img.shields.io/badge/status-production-green.svg)
![CI](https://github.com/borjamoskv/cortex/actions/workflows/ci.yml/badge.svg)
[![Docs](https://img.shields.io/badge/docs-live-brightgreen)](https://borjamoskv.github.io/cortex/)

---

## The Problem

AI agents are making millions of decisions per day. But **who verifies those decisions are correct?**

- **Mem0** stores what agents remember. But can you prove the memory wasn't tampered with?
- **Zep** builds knowledge graphs. But can you audit the chain of reasoning?
- **Letta** manages agent state. But can you generate a compliance report for regulators?

The **EU AI Act (Article 12, enforced August 2026)** requires:
- ✅ Automatic logging of all agent decisions
- ✅ Tamper-proof storage of decision records
- ✅ Full traceability and explainability
- ✅ Periodic integrity verification

**Fines: up to €30M or 6% of global revenue.**

## The Solution

CORTEX doesn't replace your memory layer — it **certifies** it.

```
Your Memory Layer (Mem0 / Zep / Letta / Custom)
        ↓
   CORTEX Trust Engine
        ├── SHA-256 hash-chained ledger
        ├── Merkle tree checkpoints
        ├── Reputation-weighted consensus
        └── EU AI Act compliance reports
```

### Core Capabilities

| Capability | What It Does | EU AI Act |
|:---|:---|:---:|
| 🔗 **Immutable Ledger** | Every fact is hash-chained. Tamper = detectable. | Art. 12.3 |
| 🌳 **Merkle Checkpoints** | Periodic batch verification of ledger integrity | Art. 12.4 |
| 📋 **Audit Trail** | Timestamped, hash-verified log of all decisions | Art. 12.1 |
| 🔍 **Decision Lineage** | Trace how an agent arrived at any conclusion | Art. 12.2d |
| 🤝 **Consensus (RWC)** | Multi-agent verification with reputation scoring | Art. 14 |
| 📊 **Compliance Report** | One-command regulatory readiness snapshot | Art. 12 |
| 🧠 **Semantic Search** | Vector + Graph-RAG hybrid retrieval | — |
| 🏠 **100% Local-First** | SQLite. No cloud. Your data, your machine. | — |

---

## Quick Start

### Install

```bash
pip install cortex-memory
```

### Store a Decision & Verify It

```bash
# Store a fact
cortex store --type decision --project my-agent "Chose OAuth2 PKCE for auth"

# Verify its cryptographic integrity
cortex verify 42
# → ✅ VERIFIED — Hash chain intact, Merkle sealed

# Generate compliance report
cortex compliance-report
# → Compliance Score: 5/5 — All Article 12 requirements met
```

### Run as MCP Server (Universal IDE Plugin)

```bash
# Works with: Claude Code, Cursor, OpenClaw, Windsurf, Antigravity
python -m cortex.mcp
```

### Run as REST API

```bash
uvicorn cortex.api:app --port 8484
```

---

## Competitive Landscape

| | **CORTEX** | Mem0 | Zep | Letta | RecordsKeeper | UtopIQ |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Cryptographic Ledger** | ✅ | ❌ | ❌ | ❌ | ✅ (blockchain) | ✅ (blockchain) |
| **Merkle Checkpoints** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Multi-Agent Consensus** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Local-First** | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **No Blockchain Overhead** | ✅ | — | — | — | ❌ | ❌ |
| **MCP Native** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **EU AI Act Ready** | ✅ | ❌ | ❌ | ❌ | Partial | Partial |
| **Cost** | **Free** | $249/mo | $$$ | Free | $$$ | $$$ |

---

## Architecture

```
┌─────────────────────────────────────────┐
│         CORTEX Trust Engine             │
├─────────────┬─────────────┬─────────────┤
│  Facts DB   │  Ledger     │  Consensus  │
│  (sqlite)   │  (SHA-256)  │  (RWC)      │
├─────────────┼─────────────┼─────────────┤
│  Embeddings │  Merkle     │  Reputation  │
│  (ONNX)     │  (Trees)    │  (Weighted)  │
├─────────────┴─────────────┴─────────────┤
│  REST API (FastAPI) │ MCP Server (stdio) │
└─────────────────────┴────────────────────┘
```

---

## Integrations

CORTEX plugs into your existing stack:

- **IDEs**: Claude Code, Cursor, OpenClaw, Windsurf, Antigravity (via MCP)
- **Frameworks**: LangChain, CrewAI, AutoGen, Google ADK
- **Memory Layers**: Sits on top of Mem0, Zep, Letta as verification layer
- **Deployment**: Docker, Kubernetes, bare metal, or just `pip install`

---

## License

**Business Source License 1.1** (BSL-1.1).
Free for non-production and development use. Converts to Apache 2.0 on 2030-01-01.
See [LICENSE](LICENSE) for details.

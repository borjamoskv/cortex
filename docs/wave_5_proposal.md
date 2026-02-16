Analyze the CORTEX V4.0 architecture and the new Consensus Layer. Propose Wave 5
(Persistence & Deployment) focusing on: 1. Immutable logging of votes. 2. 
High-availability synchronization of the ledger. 3. Edge deployment via MCP 
server optimization.
TurnBegin(
    user_input='Analyze the CORTEX V4.0 architecture and the new Consensus 
Layer. Propose Wave 5 (Persistence & Deployment) focusing on: 1. Immutable 
logging of votes. 2. High-availability synchronization of the ledger. 3. Edge 
deployment via MCP server optimization.'
)
StepBegin(n=1)
ToolCall(
    type='function',
    id='tool_P9GQfXKo7FPoU8YSZqHvMAss',
    function=FunctionBody(
        name='ReadFile',
        arguments='{"path": 
"/Users/borjafernandezangulo/cortex/CORTEX_V4_ARCHITECTURAL_SUMMARY.md"}'
    ),
    extras=None
)
ToolCall(
    type='function',
    id='tool_QWoGywUgx52wBkk45NC5ZwsX',
    function=FunctionBody(name='ReadFile', arguments=''),
    extras=None
)
ToolResult(
    tool_call_id='tool_P9GQfXKo7FPoU8YSZqHvMAss',
    return_value=ToolOk(
        is_error=False,
        output='     1\t# CORTEX V4.0 — Architectural Analysis & Wave 5 
Proposal\n     2\t## Executive Summary\n     3\t\n     4\t**Date:** 2026-02-16  
\n     5\t**Subject:** CORTEX V4.0 Architecture Review and Wave 5 (Persistence &
Deployment) Proposal  \n     6\t**Status:** Technical Design Complete\n     
7\t\n     8\t---\n     9\t\n    10\t## 1. Current Architecture Overview\n    
11\t\n    12\t### 1.1 System Components\n    13\t\n    14\t```\n    
15\t┌─────────────────────────────────────────────────────────────────────────┐\
n    16\t│                        CORTEX V4.0 ARCHITECTURE                      
│\n    
17\t├─────────────────────────────────────────────────────────────────────────┤\
n    18\t│                                                                      
│\n    19\t│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  
┌────────────┐  │\n    20\t│  │     CLI      │  │  REST API    │  │  Dashboard  
│  │   MCP      │  │\n    21\t│  │  (cortex)    │  │  (FastAPI)   │  │  (Noir 
UI)   │  │  Server    │  │\n    22\t│  └──────┬───────┘  └──────┬───────┘  
└──────┬───────┘  └─────┬──────┘  │\n    23\t│         │                 │      
│                │         │\n    24\t│         
└─────────────────┴─────────────────┴────────────────┘         │\n    25\t│     
│                                     │\n    26\t│                              
▼                                     │\n    27\t│                    
┌─────────────────────────────┐                     │\n    28\t│                
│      Core Engine Layer      │                     │\n    29\t│                
│  ┌─────────────────────┐    │                     │\n    30\t│                
│  │   CortexEngine      │    │                     │\n    31\t│                
│  │  - Facts (CRUD)     │    │                     │\n    32\t│                
│  │  - Search (semantic)│    │                     │\n    33\t│                
│  │  - Temporal queries │    │                     │\n    34\t│                
│  │  - Graph memory     │    │                     │\n    35\t│                
│  └─────────────────────┘    │                     │\n    36\t│                
│  ┌─────────────────────┐    │                     │\n    37\t│                
│  │  Consensus Layer    │◄───┼─── Wave 4          │\n    38\t│                 
│  │  - Vote casting     │    │                     │\n    39\t│                
│  │  - Score tracking   │    │                     │\n    40\t│                
│  │  - Reputation (RWC) │    │                     │\n    41\t│                
│  └─────────────────────┘    │                     │\n    42\t│                
└──────────────┬──────────────┘                     │\n    43\t│                
│                                     │\n    44\t│         
┌─────────────────────────┼─────────────────────────┐          │\n    45\t│     
│                         │                         │          │\n    46\t│     
▼                         ▼                         ▼          │\n    47\t│  
┌──────────────┐      ┌──────────────────┐      ┌──────────────┐     │\n    
48\t│  │   SQLite     │      │   sqlite-vec     │      │   Ledger     │     │\n 
49\t│  │  (Facts)     │      │ (Vector Search)  │      │ (Hash Chain) │     │\n 
50\t│  └──────────────┘      └──────────────────┘      └──────────────┘     │\n 
51\t│                                                                         
│\n    
52\t└─────────────────────────────────────────────────────────────────────────┘\
n    53\t```\n    54\t\n    55\t### 1.2 Key Features (Waves 1-4)\n    56\t\n    
57\t| Wave | Feature | Status | Description |\n    
58\t|------|---------|--------|-------------|\n    59\t| 1 | Core Engine | ✅ | 
Fact storage, semantic search, embeddings |\n    60\t| 2 | Temporal Facts | ✅ |
valid_from/valid_until, point-in-time queries |\n    61\t| 2 | Transaction 
Ledger | ✅ | Hash-chained append-only log |\n    62\t| 3 | REST API | ✅ | 
FastAPI with API key auth |\n    63\t| 3 | Dashboard | ✅ | Industrial Noir UI 
|\n    64\t| 3 | Daemon | ✅ | MOSKV-1 background watchdog |\n    65\t| 4 | 
**Consensus Layer** | ✅ | **Neural Swarm Consensus** |\n    66\t\n    67\t---\n
68\t\n    69\t## 2. Consensus Layer Deep Dive\n    70\t\n    71\t### 2.1 Current
Implementation (Wave 4)\n    72\t\n    73\tThe **Neural Swarm Consensus** system
provides distributed fact verification:\n    74\t\n    75\t```python\n    76\t# 
Current consensus formula (cortex/engine.py)\n    77\tscore = 1.0 + (vote_sum * 
0.1)  # Linear: each vote ±0.1\n    78\t\n    79\t# Thresholds\n    
80\tverified:  score >= 1.5  (5+ net votes)\n    81\tdisputed:  score <= 0.5  
(5- net votes)\n    82\tstated:    0.5 < score < 1.5\n    83\t```\n    84\t\n   
85\t**Database Schema:**\n    86\t```sql\n    87\t-- Votes table\n    88\tCREATE
TABLE consensus_votes (\n    89\t    id          INTEGER PRIMARY KEY,\n    90\t 
fact_id     INTEGER REFERENCES facts(id),\n    91\t    agent       TEXT NOT 
NULL,        -- Agent identifier\n    92\t    vote        INTEGER NOT NULL,     
-- +1 verify, -1 dispute\n    93\t    timestamp   TEXT DEFAULT 
(datetime(\'now\')),\n    94\t    UNIQUE(fact_id, agent)\n    95\t);\n    96\t\n
97\t-- Facts with consensus tracking\n    98\tALTER TABLE facts ADD COLUMN 
consensus_score REAL DEFAULT 1.0;\n    99\tALTER TABLE facts ADD COLUMN 
confidence TEXT DEFAULT \'stated\';\n   100\t```\n   101\t\n   102\t### 2.2 
Reputation-Weighted Consensus (RWC) — Future Enhancement\n   103\t\n   104\tThe 
architectural analysis (`kimi_architectural_analysis.md`) identifies the need 
for **Reputation-Weighted Consensus** to enable Sovereign AI:\n   105\t\n   
106\t```python\n   107\t# Proposed RWC formula\n   108\tscore = Σ(vote_i × 
reputation_i × decay_i) / Σ(reputation_i × decay_i)\n   109\t\n   110\t# 
Where:\n   111\t# - reputation_i: [0.0, 1.0] based on historical accuracy\n   
112\t# - decay_i: temporal decay factor e^(-age/τ)\n   113\t```\n   114\t\n   
115\t**Key Schema Additions:**\n   116\t```sql\n   117\t-- Agent registry with 
reputation\n   118\tCREATE TABLE agents (\n   119\t    id              TEXT 
PRIMARY KEY,\n   120\t    public_key      TEXT NOT NULL,\n   121\t    
reputation_score REAL DEFAULT 0.5,\n   122\t    total_votes     INTEGER DEFAULT 
0,\n   123\t    successful_votes INTEGER DEFAULT 0,\n   124\t    last_active_at 
TEXT\n   125\t);\n   126\t\n   127\t-- Trust delegation (EigenTrust-style)\n   
128\tCREATE TABLE trust_edges (\n   129\t    source_agent    TEXT REFERENCES 
agents(id),\n   130\t    target_agent    TEXT REFERENCES agents(id),\n   131\t  
trust_weight    REAL NOT NULL\n   132\t);\n   133\t```\n   134\t\n   135\t### 
2.3 Consensus Vulnerability Analysis\n   136\t\n   137\t| Attack Vector | 
Current Risk | RWC Mitigation |\n   
138\t|---------------|--------------|----------------|\n   139\t| Sybil 
(multiple identities) | 🔴 High | Reputation staking + verification |\n   140\t|
Vote stuffing | 🔴 High | Per-agent reputation weighting |\n   141\t| Ghost 
votes (old votes) | 🟡 Medium | Temporal decay factor |\n   142\t| Collusion | 
🟡 Medium | Trust graph analysis + diversity requirements |\n   143\t| Key 
compromise | 🟡 Medium | Multi-factor auth for high-rep agents |\n   144\t\n   
145\t---\n   146\t\n   147\t## 3. Security Posture\n   148\t\n   149\t### 3.1 
Hardening Status (from `HARDENING_COMPLETE.md`)\n   150\t\n   151\t| Issue | 
Severity | Status |\n   152\t|-------|----------|--------|\n   153\t| CORS 
wildcard | 🔴 P0 | ✅ Fixed — restricted origins |\n   154\t| SQL injection 
(temporal) | 🔴 P0 | ✅ Fixed — whitelist validation |\n   155\t| Path traversal
(export) | 🔴 P0 | ✅ Fixed — path sanitization |\n   156\t| Rate limiting | 🟡 
P1 | ✅ Implemented — 300 req/min |\n   157\t| Error exposure | 🟡 P1 | ✅ Fixed
— sanitized errors |\n   158\t| Atomic transactions | 🟠 P2 | ✅ Fixed — batch 
atomicity |\n   159\t\n   160\t### 3.2 Remaining Considerations\n   161\t\n   
162\t1. **Immutable Audit Logs**: Current ledger is tamper-evident but not 
tamper-proof\n   163\t2. **Connection Pooling**: SQLite connections are not 
pooled\n   164\t3. **Async Operations**: Some blocking operations in async 
context\n   165\t4. **Key Management**: No hardware security module (HSM) 
support\n   166\t\n   167\t---\n   168\t\n   169\t## 4. Wave 5: Persistence & 
Deployment\n   170\t\n   171\t### 4.1 Overview\n   172\t\n   173\tWave 5 
addresses production readiness with two main thrusts:\n   174\t\n   175\t1. 
**Immutable Audit Logs**: Cryptographic guarantees for the transaction ledger\n 
176\t2. **MCP Server Optimization**: High-performance Model Context Protocol 
integration\n   177\t\n   178\t### 4.2 Immutable Audit Logs\n   179\t\n   
180\t**Problem**: Current ledger can be modified by database admins ("God Key" 
attack)\n   181\t\n   182\t**Solution**: Hierarchical ledger with Merkle trees\n
183\t\n   184\t```\n   185\tTransaction Flow:\n   186\t┌─────────┐     
┌─────────────┐     ┌──────────────┐     ┌─────────────┐\n   187\t│  Facts  
│────▶│  Hash Chain │────▶│ Merkle Tree  │────▶│  Signature  │\n   188\t│  Table
│     │ (SHA-256)   │     │ (Batches)    │     │ (Optional)  │\n   
189\t└─────────┘     └─────────────┘     └──────────────┘     └─────────────┘\n 
190\t```\n   191\t\n   192\t**Key Features:**\n   193\t- Merkle root every 1000 
transactions for efficient verification\n   194\t- Export with integrity 
proofs\n   195\t- Tamper detection via hash chain verification\n   196\t- 
Optional external anchoring (blockchain, timestamp services)\n   197\t\n   
198\t**New CLI Commands:**\n   199\t```bash\n   200\tcortex ledger checkpoint   
# Create Merkle checkpoint\n   201\tcortex ledger verify        # Verify chain 
integrity\n   202\tcortex ledger export        # Export verifiable audit log\n  
203\t```\n   204\t\n   205\t### 4.3 MCP Server Optimization\n   206\t\n   
207\t**Current Limitations:**\n   208\t- stdio transport only\n   209\t- 
Blocking operations\n   210\t- No caching\n   211\t- Single-threaded\n   212\t\n
213\t**Optimized Architecture:**\n   214\t\n   215\t```\n   
216\t┌─────────────────────────────────────────────────────────────────┐\n   
217\t│              OPTIMIZED MCP SERVER (v2)                          │\n   
218\t├─────────────────────────────────────────────────────────────────┤\n   
219\t│                                                                 │\n   
220\t│   Transports:  [stdio] [SSE] [WebSocket] [HTTP/2]              │\n   
221\t│                         │                                       │\n   
222\t│                         ▼                                       │\n   
223\t│            ┌─────────────────────┐                             │\n   
224\t│            │   Async Handler     │                             │\n   
225\t│            │   (Connection Pool) │                             │\n   
226\t│            └──────────┬──────────┘                             │\n   
227\t│                       │                                         │\n   
228\t│       ┌───────────────┼───────────────┐                       │\n   
229\t│       ▼               ▼               ▼                       │\n   
230\t│   ┌────────┐     ┌────────┐     ┌────────┐                   │\n   231\t│
│ Cache  │     │ Batch  │     │Metrics │                   │\n   232\t│   │ 
(LRU)  │     │  Ops   │     │        │                   │\n   233\t│   
└────────┘     └────────┘     └────────┘                   │\n   234\t│         
│\n   235\t└─────────────────────────────────────────────────────────────────┘\n
236\t```\n   237\t\n   238\t**Performance Targets:**\n   239\t\n   240\t| Metric
| Current | Target | Speedup |\n   
241\t|--------|---------|--------|---------|\n   242\t| Cold search | 50ms | 
50ms | — |\n   243\t| Warm search | 50ms | 1ms | **50x** |\n   244\t| Batch 
store (100) | 2300ms | 450ms | **5x** |\n   245\t| Throughput | 100 req/s | 1000
req/s | **10x** |\n   246\t\n   247\t### 4.4 Deployment Patterns\n   248\t\n   
249\t**Docker:**\n   250\t```dockerfile\n   251\tFROM python:3.12-slim\n   
252\t# Multi-stage build, <200MB image\n   253\t# Health checks, non-root user\n
254\t```\n   255\t\n   256\t**Kubernetes:**\n   257\t```yaml\n   258\t# 
StatefulSet for data persistence\n   259\t# 3 replicas with anti-affinity\n   
260\t# PersistentVolumeClaim for SQLite\n   261\t```\n   262\t\n   
263\t**systemd:**\n   264\t```ini\n   265\t[Service]\n   266\tType=simple\n   
267\tUser=cortex\n   268\tProtectSystem=strict\n   269\tProtectHome=true\n   
270\t```\n   271\t\n   272\t---\n   273\t\n   274\t## 5. Technical Debt 
Register\n   275\t\n   276\t| Item | Priority | Effort | Impact |\n   
277\t|------|----------|--------|--------|\n   278\t| Connection pooling | P1 | 
8h | Better concurrency |\n   279\t| Async SQLite | P2 | 16h | Remove blocking 
ops |\n   280\t| HSM key support | P3 | 24h | Enterprise security |\n   281\t| 
Graph query language | P3 | 40h | Advanced analytics |\n   282\t\n   283\t---\n 
284\t\n   285\t## 6. Recommendations\n   286\t\n   287\t### 6.1 Immediate 
(Pre-Production)\n   288\t\n   289\t1. ✅ **Complete Wave 5 Implementation** (4 
weeks)\n   290\t   - Immutable ledger with Merkle trees\n   291\t   - Optimized 
MCP server\n   292\t   - Docker/K8s deployment\n   293\t\n   294\t2. ✅ **Load 
Testing**\n   295\t   - 10k requests/sec sustained\n   296\t   - 1M fact 
database\n   297\t   - Consensus under load\n   298\t\n   299\t3. ✅ **Security 
Audit**\n   300\t   - Penetration testing\n   301\t   - Dependency scanning\n   
302\t   - Key management review\n   303\t\n   304\t### 6.2 Short-Term (3 
months)\n   305\t\n   306\t1. **RWC Phase 1**: Agent registry with basic 
reputation\n   307\t2. **Bridge Protocols**: GitHub, Linear integrations\n   
308\t3. **Metrics Pipeline**: Prometheus + Grafana\n   309\t\n   310\t### 6.3 
Long-Term (6-12 months)\n   311\t\n   312\t1. **Swarm Federation**: Multi-node 
consensus\n   313\t2. **Zero-Knowledge Proofs**: Private voting\n   314\t3. 
**Cross-Chain Anchoring**: Bitcoin/Ethereum proofs\n   315\t\n   316\t---\n   
317\t\n   318\t## 7. Wave 5 Deliverables\n   319\t\n   320\t### 7.1 Code\n   
321\t\n   322\t| File | Description |\n   323\t|------|-------------|\n   324\t|
`cortex/ledger.py` | Merkle tree + immutable ledger |\n   325\t| 
`cortex/mcp_server_v2.py` | Optimized MCP server |\n   326\t| 
`cortex/routes/ledger.py` | Ledger API endpoints |\n   327\t| 
`tests/benchmark_mcp.py` | Performance benchmarks |\n   328\t\n   329\t### 7.2 
Configuration\n   330\t\n   331\t| File | Description |\n   
332\t|------|-------------|\n   333\t| `Dockerfile.production` | Production 
Docker image |\n   334\t| `docker-compose.yml` | Multi-service deployment |\n   
335\t| `deploy/cortex.service` | systemd service |\n   336\t| 
`deploy/k8s-deployment.yaml` | Kubernetes manifests |\n   337\t\n   338\t### 7.3
Documentation\n   339\t\n   340\t| File | Description |\n   
341\t|------|-------------|\n   342\t| `WAVE5_PERSISTENCE_DEPLOYMENT.md` | Full 
technical spec |\n   343\t| `docs/deployment.md` | Deployment guide |\n   344\t|
`docs/ledger.md` | Ledger architecture |\n   345\t\n   346\t---\n   347\t\n   
348\t## 8. Success Metrics\n   349\t\n   350\t### 8.1 Technical Metrics\n   
351\t\n   352\t| Metric | Target | Measurement |\n   
353\t|--------|--------|-------------|\n   354\t| Ledger verification | <100ms |
10k transactions |\n   355\t| MCP cold query | <50ms | p99 latency |\n   356\t| 
MCP warm query | <1ms | p99 latency |\n   357\t| MCP throughput | >1000 req/s | 
Load test |\n   358\t| Cache hit rate | >80% | Runtime metrics |\n   359\t| 
Docker image | <200MB | `docker images` |\n   360\t\n   361\t### 8.2 Adoption 
Metrics\n   362\t\n   363\t| Metric | Target |\n   364\t|--------|--------|\n   
365\t| API uptime | 99.9% |\n   366\t| Error rate | <0.1% |\n   367\t| Mean 
recovery time | <5 minutes |\n   368\t\n   369\t---\n   370\t\n   371\t## 
Appendix: File References\n   372\t\n   373\t### Core Architecture\n   374\t- 
`cortex/engine.py` — Core engine with consensus\n   375\t- `cortex/schema.py` — 
Database schema definitions\n   376\t- `cortex/migrations.py` — Schema 
migrations\n   377\t\n   378\t### Consensus Layer\n   379\t- 
`kimi_architectural_analysis.md` — RWC detailed proposal\n   380\t- 
`test_consensus_flow.db*` — Consensus test database\n   381\t\n   382\t### 
Security\n   383\t- `SECURITY_ARCHITECTURE_AUDIT_V4.md` — Security audit 
results\n   384\t- `HARDENING_COMPLETE.md` — Hardening status\n   385\t\n   
386\t### Wave 5 Proposal\n   387\t- `WAVE5_PERSISTENCE_DEPLOYMENT.md` — Full 
technical specification\n   388\t\n   389\t---\n   390\t\n   391\t**End of 
Summary**\n   392\t\n   393\t*Prepared for CORTEX V4.0 Architecture Review | 
2026-02-16*\n',
        message='393 lines read from file starting from line 1. End of file 
reached.',
        display=[],
        extras=None
    )
)
ToolCallPart(
    arguments_part='{"path": 
"/Users/borjafernandezangulo/cortex/WAVE5_PERSISTENCE_DEPLOYMENT.md"}'
)
ToolCall(
    type='function',
    id='tool_0KuCT4gdUe8lbTCoegkSP7yz',
    function=FunctionBody(name='ReadFile', arguments='{"path":'),
    extras=None
)
ToolResult(
    tool_call_id='tool_QWoGywUgx52wBkk45NC5ZwsX',
    return_value=ToolOk(
        is_error=False,
        output='     1\t# CORTEX V4.0 — Wave 5: Persistence & Deployment\n     
2\t## Immutable Audit Logs & MCP Server Optimization\n     3\t\n     
4\t**Date:** 2026-02-16  \n     5\t**Version:** 4.1.0-alpha  \n     
6\t**Status:** Proposal / Design Document  \n     7\t**Author:** CORTEX 
Architectural Analysis\n     8\t\n     9\t---\n    10\t\n    11\t## Executive 
Summary\n    12\t\n    13\tWave 5 focuses on **production hardening** for CORTEX
V4.0\'s Consensus Layer. Building upon the Reputation-Weighted Consensus (RWC) 
foundation from Wave 4, this wave delivers:\n    14\t\n    15\t1. **Immutable 
Audit Logs** — Cryptographically tamper-evident transaction ledger\n    16\t2. 
**MCP Server Optimization** — High-performance Model Context Protocol 
integration\n    17\t3. **Deployment Readiness** — Docker, systemd, and 
cloud-native deployment patterns\n    18\t\n    19\t### Wave Completion Status\n
20\t\n    21\t| Wave | Feature | Status |\n    22\t|------|---------|--------|\n
23\t| Wave 1 | Core Engine (Facts, Search, Embeddings) | ✅ Complete |\n    
24\t| Wave 2 | Temporal Facts & Transaction Ledger | ✅ Complete |\n    25\t| 
Wave 3 | REST API, Auth, Dashboard | ✅ Complete |\n    26\t| Wave 4 | Consensus
Layer (RWC) | ✅ Complete |\n    27\t| **Wave 5** | **Persistence & Deployment**
| 🔄 **Proposed** |\n    28\t| Wave 6 | Swarm Federation & Bridge Protocols | 📋
Planned |\n    29\t\n    30\t---\n    31\t\n    32\t## 1. Immutable Audit Logs\n
33\t\n    34\t### 1.1 Problem Statement\n    35\t\n    36\tThe current 
transaction ledger in `engine.py` uses simple SHA-256 chaining:\n    37\t\n    
38\t```python\n    39\t# Current Implementation (Wave 3)\n    40\thash_input = 
f"{prev_hash}:{project}:{action}:{detail_json}:{ts}"\n    41\ttx_hash = 
hashlib.sha256(hash_input.encode()).hexdigest()\n    42\t```\n    43\t\n    
44\t**Vulnerabilities:**\n    45\t- ✅ Tamper-evident but not tamper-proof 
(admins can modify SQLite directly)\n    46\t- ❌ No external verification 
mechanism\n    47\t- ❌ No proof-of-existence timestamping\n    48\t- ❌ 
Vulnerable to "God Key" attacks (database admin compromise)\n    49\t\n    
50\t### 1.2 Design Goals\n    51\t\n    52\t| Goal | Priority | Description |\n 
53\t|------|----------|-------------|\n    54\t| **Tamper-Proof** | P0 | 
Cryptographic guarantees against any modification |\n    55\t| **Verifiable** | 
P0 | Third parties can verify integrity without trust |\n    56\t| **Efficient**
| P1 | <5ms overhead per transaction |\n    57\t| **Exportable** | P1 | JSON/CSV
export for external auditors |\n    58\t| **Redundant** | P2 | Multiple storage 
backends (local + remote hash log) |\n    59\t\n    60\t### 1.3 Architecture: 
Hierarchical Ledger System\n    61\t\n    62\t```\n    
63\t┌─────────────────────────────────────────────────────────────────────┐\n   
64\t│                    IMMUTABLE LEDGER ARCHITECTURE                      │\n 
65\t├─────────────────────────────────────────────────────────────────────┤\n   
66\t│                                                                       │\n 
67\t│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐         │\n  
68\t│   │  Fact Store  │     │  Hash Chain  │     │  Merkle Tree │         │\n  
69\t│   │   (SQLite)   │────▶│   (SQLite)   │────▶│  (Periodic)  │         │\n  
70\t│   └──────────────┘     └──────────────┘     └──────────────┘         │\n  
71\t│          │                    │                    │                 │\n  
72\t│          ▼                    ▼                    ▼                 │\n  
73\t│   ┌────────────────────────────────────────────────────────────┐    │\n   
74\t│   │              EXTERNAL SIGNATURE LAYER (Optional)            │    │\n  
75\t│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │    │\n   
76\t│   │  │  Signify    │  │  OpenPubKey │  │  Anchoring  │         │    │\n   
77\t│   │  │  (Sigstore) │  │  (SSH/PGP)  │  │  (Optional) │         │    │\n   
78\t│   │  └─────────────┘  └─────────────┘  └─────────────┘         │    │\n   
79\t│   └────────────────────────────────────────────────────────────┘    │\n   
80\t│                                                                       │\n 
81\t└─────────────────────────────────────────────────────────────────────┘\n   
82\t```\n    83\t\n    84\t### 1.4 Database Schema Extensions\n    85\t\n    
86\t```sql\n    87\t-- 
============================================================\n    88\t-- 
MIGRATION 009: Immutable Ledger Enhancements\n    89\t-- 
============================================================\n    90\t\n    
91\t-- Merkle tree roots for periodic integrity verification\n    92\tCREATE 
TABLE merkle_roots (\n    93\t    id              INTEGER PRIMARY KEY 
AUTOINCREMENT,\n    94\t    root_hash       TEXT NOT NULL,              -- 
SHA-256 of combined TX hashes\n    95\t    tx_start_id     INTEGER NOT NULL,    
-- First TX in this batch\n    96\t    tx_end_id       INTEGER NOT NULL,        
-- Last TX in this batch\n    97\t    tx_count        INTEGER NOT NULL,\n    
98\t    created_at      TEXT NOT NULL DEFAULT (datetime(\'now\')),\n    99\t    
\n   100\t    -- Optional: External proof-of-existence\n   101\t    
external_proof  TEXT,                       -- URL or hash of external anchor\n 
102\t    \n   103\t    -- Signature by "God Key" (if configured)\n   104\t    
signature       TEXT                        -- Ed25519 signature of root_hash\n 
105\t);\n   106\t\n   107\tCREATE INDEX idx_merkle_range ON 
merkle_roots(tx_start_id, tx_end_id);\n   108\t\n   109\t-- Audit log export 
tracking\n   110\tCREATE TABLE audit_exports (\n   111\t    id              
INTEGER PRIMARY KEY AUTOINCREMENT,\n   112\t    export_type     TEXT NOT NULL,  
-- \'json\', \'csv\', \'chain\'\n   113\t    filename        TEXT NOT NULL,\n   
114\t    file_hash       TEXT NOT NULL,              -- SHA-256 of exported 
file\n   115\t    tx_start_id     INTEGER NOT NULL,\n   116\t    tx_end_id      
INTEGER NOT NULL,\n   117\t    exported_at     TEXT NOT NULL DEFAULT 
(datetime(\'now\')),\n   118\t    exported_by     TEXT NOT NULL               --
API key or agent ID\n   119\t);\n   120\t\n   121\t-- Tamper detection log 
(append-only by design)\n   122\tCREATE TABLE integrity_checks (\n   123\t    id
INTEGER PRIMARY KEY AUTOINCREMENT,\n   124\t    check_type      TEXT NOT NULL,  
-- \'merkle\', \'chain\', \'full\'\n   125\t    status          TEXT NOT NULL,  
-- \'ok\', \'violation\', \'error\'\n   126\t    details         TEXT,          
-- JSON with findings\n   127\t    started_at      TEXT NOT NULL,\n   128\t    
completed_at    TEXT NOT NULL\n   129\t);\n   130\t```\n   131\t\n   132\t### 
1.5 Implementation: Merkle Tree\n   133\t\n   134\t```python\n   135\t# 
cortex/ledger.py\n   136\t"""\n   137\tImmutable Ledger — Cryptographic 
integrity for CORTEX transactions.\n   138\t"""\n   139\t\n   140\timport 
hashlib\n   141\timport json\n   142\tfrom typing import List, Optional, Tuple\n
143\tfrom dataclasses import dataclass\n   144\t\n   145\t\n   146\t@dataclass\n
147\tclass MerkleNode:\n   148\t    """Node in the Merkle tree."""\n   149\t    
hash: str\n   150\t    left: Optional[\'MerkleNode\'] = None\n   151\t    right:
Optional[\'MerkleNode\'] = None\n   152\t    is_leaf: bool = False\n   153\t\n  
154\t\n   155\tclass MerkleTree:\n   156\t    """\n   157\t    Merkle tree for 
batch transaction verification.\n   158\t    Allows efficient verification of 
large transaction sets.\n   159\t    """\n   160\t    \n   161\t    def 
__init__(self, leaves: List[str]):\n   162\t        """\n   163\t        Build a
Merkle tree from leaf hashes.\n   164\t        \n   165\t        Args:\n   166\t
leaves: List of SHA-256 hashes (transaction hashes)\n   167\t        """\n   
168\t        self.leaves = leaves\n   169\t        self.root = 
self._build_tree(leaves)\n   170\t    \n   171\t    def _hash_pair(self, left: 
str, right: str) -> str:\n   172\t        """Hash two child hashes 
together."""\n   173\t        combined = left + right\n   174\t        return 
hashlib.sha256(combined.encode()).hexdigest()\n   175\t    \n   176\t    def 
_build_tree(self, hashes: List[str]) -> Optional[MerkleNode]:\n   177\t        
"""Recursively build the tree bottom-up."""\n   178\t        if not hashes:\n   
179\t            return None\n   180\t        \n   181\t        if len(hashes) 
== 1:\n   182\t            return MerkleNode(hash=hashes[0], is_leaf=True)\n   
183\t        \n   184\t        # Pair up hashes\n   185\t        next_level = 
[]\n   186\t        for i in range(0, len(hashes), 2):\n   187\t            left
= hashes[i]\n   188\t            right = hashes[i + 1] if i + 1 < len(hashes) 
else hashes[i]\n   189\t            combined_hash = self._hash_pair(left, 
right)\n   190\t            next_level.append(combined_hash)\n   191\t        \n
192\t        return self._build_tree(next_level)\n   193\t    \n   194\t    def 
get_root(self) -> Optional[str]:\n   195\t        """Get the root hash of the 
tree."""\n   196\t        return self.root.hash if self.root else None\n   197\t
\n   198\t    def get_proof(self, index: int) -> List[Tuple[str, str]]:\n   
199\t        """\n   200\t        Get a Merkle proof for a leaf at the given 
index.\n   201\t        \n   202\t        Returns:\n   203\t            List of 
(sibling_hash, direction) tuples where direction is \'L\' or \'R\'\n   204\t    
"""\n   205\t        proof = []\n   206\t        current_idx = index\n   207\t  
current_level = self.leaves\n   208\t        \n   209\t        while 
len(current_level) > 1:\n   210\t            next_level = []\n   211\t          
for i in range(0, len(current_level), 2):\n   212\t                left = 
current_level[i]\n   213\t                right = current_level[i + 1] if i + 1 
< len(current_level) else current_level[i]\n   214\t                \n   215\t  
if i == current_idx or (i + 1 == current_idx and i + 1 < len(current_level)):\n 
216\t                    # Found our node at this level\n   217\t               
if current_idx == i:\n   218\t                        proof.append((right, 
\'R\'))\n   219\t                    else:\n   220\t                        
proof.append((left, \'L\'))\n   221\t                \n   222\t                
combined = self._hash_pair(left, right)\n   223\t                
next_level.append(combined)\n   224\t            \n   225\t            
current_idx //= 2\n   226\t            current_level = next_level\n   227\t     
\n   228\t        return proof\n   229\t    \n   230\t    def verify_proof(self,
leaf_hash: str, proof: List[Tuple[str, str]], root: str) -> bool:\n   231\t     
"""Verify a Merkle proof."""\n   232\t        current = leaf_hash\n   233\t     
for sibling, direction in proof:\n   234\t            if direction == \'L\':\n  
235\t                current = self._hash_pair(sibling, current)\n   236\t      
else:\n   237\t                current = self._hash_pair(current, sibling)\n   
238\t        return current == root\n   239\t\n   240\t\n   241\tclass 
ImmutableLedger:\n   242\t    """\n   243\t    Manages the cryptographic 
integrity of the CORTEX transaction ledger.\n   244\t    \n   245\t    
Features:\n   246\t    - Periodic Merkle tree generation\n   247\t    - Tamper 
detection via hash verification\n   248\t    - Export with integrity proofs\n   
249\t    """\n   250\t    \n   251\t    MERKLE_BATCH_SIZE = 1000  # Create 
Merkle root every N transactions\n   252\t    \n   253\t    def __init__(self, 
conn: sqlite3.Connection):\n   254\t        self.conn = conn\n   255\t    \n   
256\t    def compute_merkle_root(self, start_id: int, end_id: int) -> 
Optional[str]:\n   257\t        """Compute Merkle root for a range of 
transactions."""\n   258\t        cursor = self.conn.execute(\n   259\t         
"SELECT hash FROM transactions WHERE id >= ? AND id <= ? ORDER BY id",\n   260\t
(start_id, end_id)\n   261\t        )\n   262\t        hashes = [row[0] for row 
in cursor.fetchall()]\n   263\t        \n   264\t        if not hashes:\n   
265\t            return None\n   266\t        \n   267\t        tree = 
MerkleTree(hashes)\n   268\t        return tree.get_root()\n   269\t    \n   
270\t    def create_merkle_checkpoint(self) -> Optional[int]:\n   271\t        
"""\n   272\t        Create a Merkle tree checkpoint for recent transactions.\n 
273\t        Returns the checkpoint ID or None if no new transactions.\n   274\t
"""\n   275\t        # Find last checkpoint\n   276\t        last = 
self.conn.execute(\n   277\t            "SELECT MAX(tx_end_id) FROM 
merkle_roots"\n   278\t        ).fetchone()[0] or 0\n   279\t        \n   280\t 
# Count new transactions\n   281\t        count = self.conn.execute(\n   282\t  
"SELECT COUNT(*) FROM transactions WHERE id > ?",\n   283\t            (last,)\n
284\t        ).fetchone()[0]\n   285\t        \n   286\t        if count < 
self.MERKLE_BATCH_SIZE:\n   287\t            return None  # Not enough 
transactions\n   288\t        \n   289\t        # Get range\n   290\t        
start = last + 1\n   291\t        end_row = self.conn.execute(\n   292\t        
"SELECT id FROM transactions WHERE id > ? ORDER BY id LIMIT 1 OFFSET ?",\n   
293\t            (last, self.MERKLE_BATCH_SIZE - 1)\n   294\t        
).fetchone()\n   295\t        end = end_row[0] if end_row else start\n   296\t  
\n   297\t        # Compute root\n   298\t        root = 
self.compute_merkle_root(start, end)\n   299\t        if not root:\n   300\t    
return None\n   301\t        \n   302\t        # Store checkpoint\n   303\t     
cursor = self.conn.execute(\n   304\t            """INSERT INTO merkle_roots \n 
305\t                (root_hash, tx_start_id, tx_end_id, tx_count) \n   306\t   
VALUES (?, ?, ?, ?)""",\n   307\t            (root, start, end, end - start + 
1)\n   308\t        )\n   309\t        self.conn.commit()\n   310\t        \n   
311\t        return cursor.lastrowid\n   312\t    \n   313\t    def 
verify_chain_integrity(self) -> dict:\n   314\t        """\n   315\t        
Verify the integrity of the entire transaction chain.\n   316\t        \n   
317\t        Returns:\n   318\t            Dict with verification results\n   
319\t        """\n   320\t        violations = []\n   321\t        \n   322\t   
# 1. Verify hash chain continuity\n   323\t        transactions = 
self.conn.execute(\n   324\t            "SELECT id, prev_hash, hash, project, 
action, detail, timestamp "\n   325\t            "FROM transactions ORDER BY 
id"\n   326\t        ).fetchall()\n   327\t        \n   328\t        prev_hash =
"GENESIS"\n   329\t        for tx in transactions:\n   330\t            tx_id, 
tx_prev, tx_hash, project, action, detail, ts = tx\n   331\t            \n   
332\t            # Verify prev_hash matches\n   333\t            if tx_prev != 
prev_hash:\n   334\t                violations.append({\n   335\t               
"tx_id": tx_id,\n   336\t                    "type": "chain_break",\n   337\t   
"expected_prev": prev_hash,\n   338\t                    "actual_prev": 
tx_prev\n   339\t                })\n   340\t            \n   341\t            #
Verify current hash\n   342\t            hash_input = 
f"{tx_prev}:{project}:{action}:{detail}:{ts}"\n   343\t            computed = 
hashlib.sha256(hash_input.encode()).hexdigest()\n   344\t            \n   345\t 
if computed != tx_hash:\n   346\t                violations.append({\n   347\t  
"tx_id": tx_id,\n   348\t                    "type": "hash_mismatch",\n   349\t 
"computed": computed,\n   350\t                    "stored": tx_hash\n   351\t  
})\n   352\t            \n   353\t            prev_hash = tx_hash\n   354\t     
\n   355\t        # 2. Verify Merkle roots\n   356\t        merkles = 
self.conn.execute(\n   357\t            "SELECT id, root_hash, tx_start_id, 
tx_end_id FROM merkle_roots ORDER BY id"\n   358\t        ).fetchall()\n   359\t
\n   360\t        for m in merkles:\n   361\t            m_id, stored_root, 
start, end = m\n   362\t            computed_root = 
self.compute_merkle_root(start, end)\n   363\t            \n   364\t            
if computed_root != stored_root:\n   365\t                violations.append({\n 
366\t                    "merkle_id": m_id,\n   367\t                    "type":
"merkle_mismatch",\n   368\t                    "range": f"{start}-{end}",\n   
369\t                    "computed": computed_root,\n   370\t                   
"stored": stored_root\n   371\t                })\n   372\t        \n   373\t   
return {\n   374\t            "valid": len(violations) == 0,\n   375\t          
"violations": violations,\n   376\t            "transactions_checked": 
len(transactions),\n   377\t            "merkle_roots_checked": len(merkles)\n  
378\t        }\n   379\t    \n   380\t    def export_verifiable_log(self, 
output_path: str, start_id: int = 1) -> dict:\n   381\t        """\n   382\t    
Export transactions with integrity proofs.\n   383\t        \n   384\t        
Args:\n   385\t            output_path: Where to write the export (JSON 
format)\n   386\t            start_id: Starting transaction ID\n   387\t        
\n   388\t        Returns:\n   389\t            Export metadata with root hash 
for verification\n   390\t        """\n   391\t        transactions = 
self.conn.execute(\n   392\t            "SELECT * FROM transactions WHERE id >= 
? ORDER BY id",\n   393\t            (start_id,)\n   394\t        ).fetchall()\n
395\t        \n   396\t        # Build Merkle tree\n   397\t        hashes = 
[tx[4] for tx in transactions]  # hash column\n   398\t        tree = 
MerkleTree(hashes)\n   399\t        root = tree.get_root()\n   400\t        \n  
401\t        export_data = {\n   402\t            "export": {\n   403\t         
"version": "1.0",\n   404\t                "exported_at": 
datetime.utcnow().isoformat(),\n   405\t                "start_id": start_id,\n 
406\t                "end_id": transactions[-1][0] if transactions else 
start_id,\n   407\t                "transaction_count": len(transactions),\n   
408\t                "merkle_root": root\n   409\t            },\n   410\t      
"transactions": [\n   411\t                {\n   412\t                    "id": 
tx[0],\n   413\t                    "project": tx[1],\n   414\t                 
"action": tx[2],\n   415\t                    "detail": json.loads(tx[3]) if 
tx[3] else None,\n   416\t                    "prev_hash": tx[4],\n   417\t     
"hash": tx[5],\n   418\t                    "timestamp": tx[6]\n   419\t        
}\n   420\t                for tx in transactions\n   421\t            ]\n   
422\t        }\n   423\t        \n   424\t        with open(output_path, \'w\') 
as f:\n   425\t            json.dump(export_data, f, indent=2)\n   426\t        
\n   427\t        # Compute file hash\n   428\t        with open(output_path, 
\'rb\') as f:\n   429\t            file_hash = 
hashlib.sha256(f.read()).hexdigest()\n   430\t        \n   431\t        # Record
export\n   432\t        self.conn.execute(\n   433\t            """INSERT INTO 
audit_exports \n   434\t                (export_type, filename, file_hash, 
tx_start_id, tx_end_id, exported_by)\n   435\t                VALUES (?, ?, ?, 
?, ?, ?)""",\n   436\t            ("json", output_path, file_hash, \n   437\t   
export_data["export"]["start_id"],\n   438\t             
export_data["export"]["end_id"],\n   439\t             "system")\n   440\t      
)\n   441\t        self.conn.commit()\n   442\t        \n   443\t        return 
{\n   444\t            "output_path": output_path,\n   445\t            
"file_hash": file_hash,\n   446\t            "merkle_root": root,\n   447\t     
"transactions": len(transactions)\n   448\t        }\n   449\t```\n   450\t\n   
451\t### 1.6 CLI Commands\n   452\t\n   453\t```bash\n   454\t# Create a Merkle 
checkpoint\n   455\tcortex ledger checkpoint\n   456\t\n   457\t# Verify ledger 
integrity\n   458\tcortex ledger verify\n   459\t# Output: ✓ Chain valid (10,234
transactions, 10 Merkle roots)\n   460\t#         ✓ All Merkle roots verified\n 
461\t#         ✓ No tampering detected\n   462\t\n   463\t# Export verifiable 
audit log\n   464\tcortex ledger export --format json --output audit_2024.json\n
465\t\n   466\t# Import and verify external audit log\n   467\tcortex ledger 
verify-external audit_2024.json\n   468\t```\n   469\t\n   470\t---\n   471\t\n 
472\t## 2. MCP Server Optimization\n   473\t\n   474\t### 2.1 Current State 
Analysis\n   475\t\n   476\tThe existing MCP server (`cortex/mcp_server.py`) 
provides basic functionality but has limitations:\n   477\t\n   478\t| Aspect | 
Current | Target |\n   479\t|--------|---------|--------|\n   480\t| Transport |
stdio only | stdio + SSE + WebSocket |\n   481\t| Concurrency | Blocking | Async
with connection pooling |\n   482\t| Caching | None | LRU for embeddings + query
results |\n   483\t| Batching | None | Multi-fact operations |\n   484\t| 
Observability | Basic logging | Metrics + structured traces |\n   485\t\n   
486\t### 2.2 Optimized Architecture\n   487\t\n   488\t```\n   
489\t┌─────────────────────────────────────────────────────────────────────┐\n  
490\t│                    OPTIMIZED MCP SERVER ARCHITECTURE                  │\n
491\t├─────────────────────────────────────────────────────────────────────┤\n  
492\t│                                                                       │\n
493\t│   ┌──────────────────────────────────────────────────────────────┐   │\n 
494\t│   │                      Transport Layer                          │   │\n
495\t│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │   │\n 
496\t│   │  │  stdio   │  │   SSE    │  │  HTTP/2  │  │  WebSocket   │  │   │\n 
497\t│   │  │(default) │  │ (server) │  │(streaming│  │ (real-time)  │  │   │\n 
498\t│   │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │   │\n 
499\t│   │       └─────────────┴─────────────┴───────────────┘           │   │\n
500\t│   │                         │                                     │   │\n
501\t│   │                         ▼                                     │   │\n
502\t│   │              ┌─────────────────────┐                         │   │\n 
503\t│   │              │   Protocol Handler  │                         │   │\n 
504\t│   │              │   (MCP 2024-11-05)  │                         │   │\n 
505\t│   │              └──────────┬──────────┘                         │   │\n 
506\t│   └─────────────────────────┼────────────────────────────────────┘   │\n 
507\t│                             │                                        │\n 
508\t│   ┌─────────────────────────┼────────────────────────────────────┐   │\n 
509\t│   │              ┌──────────▼──────────┐                          │   │\n
510\t│   │              │    Request Router   │                          │   │\n
511\t│   │              └──────────┬──────────┘                          │   │\n
512\t│   │                         │                                      │   
│\n   513\t│   │   ┌─────────────────────┼─────────────────────┐               │
│\n   514\t│   │   │                     │                     │               │
│\n   515\t│   │   ▼                     ▼                     ▼               │
│\n   516\t│   │ ┌──────────┐      ┌──────────┐      ┌──────────────────┐     │ 
│\n   517\t│   │ │  Tools   │      │Resources │      │  Prompt Templates │     │
│\n   518\t│   │ │ Registry │      │ Registry │      │    Registry      │     │ 
│\n   519\t│   │ └────┬─────┘      └────┬─────┘      └────────┬─────────┘     │ 
│\n   520\t│   │      │                 │                     │               │ 
│\n   521\t│   └──────┼─────────────────┼─────────────────────┼───────────────┘ 
│\n   522\t│          │                 │                     │                 
│\n   523\t│   ┌──────▼─────────────────▼─────────────────────▼───────────────┐ 
│\n   524\t│   │                     Engine Layer                               
│   │\n   525\t│   │  ┌──────────────┐  ┌──────────────┐  
┌─────────────────────┐  │   │\n   526\t│   │  │Query Cache   │  │ Write-Ahead  
│  │ Connection Pool     │  │   │\n   527\t│   │  │   (LRU)      │  │   Buffer  
│  │    (SQLite WAL)     │  │   │\n   528\t│   │  └──────────────┘  
└──────────────┘  └─────────────────────┘  │   │\n   529\t│   
└──────────────────────────────────────────────────────────────┘   │\n   530\t│ 
│\n   
531\t└─────────────────────────────────────────────────────────────────────┘\n  
532\t```\n   533\t\n   534\t### 2.3 Implementation: Optimized MCP Server\n   
535\t\n   536\t```python\n   537\t# cortex/mcp_server_v2.py\n   538\t"""\n   
539\tCORTEX MCP Server v2 — High-Performance Multi-Transport Implementation.\n  
540\t\n   541\tFeatures:\n   542\t- Async I/O with connection pooling\n   543\t-
Multiple transports (stdio, SSE, WebSocket)\n   544\t- Intelligent caching\n   
545\t- Batch operations\n   546\t- Comprehensive metrics\n   547\t"""\n   
548\t\n   549\tfrom __future__ import annotations\n   550\t\n   551\timport 
asyncio\n   552\timport json\n   553\timport logging\n   554\timport time\n   
555\tfrom contextlib import asynccontextmanager\n   556\tfrom dataclasses import
dataclass, field\n   557\tfrom functools import lru_cache\n   558\tfrom typing 
import Any, AsyncIterator, Callable, Dict, List, Optional, Union\n   559\t\n   
560\timport sqlite3\n   561\tfrom concurrent.futures import ThreadPoolExecutor\n
562\t\n   563\tlogger = logging.getLogger("cortex.mcp.v2")\n   564\t\n   565\t# 
─────────────────────────────────────────────────────────────────────────\n   
566\t# Configuration\n   567\t# 
─────────────────────────────────────────────────────────────────────────\n   
568\t\n   569\t@dataclass\n   570\tclass MCPServerConfig:\n   571\t    
"""Configuration for MCP server."""\n   572\t    db_path: str = 
"~/.cortex/cortex.db"\n   573\t    max_workers: int = 4\n   574\t    
query_cache_size: int = 1000\n   575\t    embedding_cache_size: int = 100\n   
576\t    batch_size: int = 100\n   577\t    enable_metrics: bool = True\n   
578\t    transport: str = "stdio"  # "stdio", "sse", "websocket"\n   579\t    \n
580\t    # SSE/WebSocket specific\n   581\t    host: str = "127.0.0.1"\n   582\t
port: int = 9999\n   583\t    keepalive_interval: float = 30.0\n   584\t\n   
585\t\n   586\t# 
─────────────────────────────────────────────────────────────────────────\n   
587\t# Metrics Collection\n   588\t# 
─────────────────────────────────────────────────────────────────────────\n   
589\t\n   590\t@dataclass\n   591\tclass MCPMetrics:\n   592\t    """Runtime 
metrics for the MCP server."""\n   593\t    requests_total: int = 0\n   594\t   
requests_by_tool: Dict[str, int] = field(default_factory=dict)\n   595\t    
request_duration_ms: List[float] = field(default_factory=list)\n   596\t    
cache_hits: int = 0\n   597\t    cache_misses: int = 0\n   598\t    
errors_total: int = 0\n   599\t    active_connections: int = 0\n   600\t    \n  
601\t    def record_request(self, tool: str, duration_ms: float, cached: bool = 
False):\n   602\t        self.requests_total += 1\n   603\t        
self.requests_by_tool[tool] = self.requests_by_tool.get(tool, 0) + 1\n   604\t  
self.request_duration_ms.append(duration_ms)\n   605\t        \n   606\t        
if cached:\n   607\t            self.cache_hits += 1\n   608\t        else:\n   
609\t            self.cache_misses += 1\n   610\t        \n   611\t        # 
Keep only last 1000 durations\n   612\t        if len(self.request_duration_ms) 
> 1000:\n   613\t            self.request_duration_ms = 
self.request_duration_ms[-1000:]\n   614\t    \n   615\t    def 
record_error(self):\n   616\t        self.errors_total += 1\n   617\t    \n   
618\t    def get_summary(self) -> dict:\n   619\t        durations = 
self.request_duration_ms\n   620\t        return {\n   621\t            
"requests_total": self.requests_total,\n   622\t            "requests_by_tool": 
self.requests_by_tool,\n   623\t            "avg_duration_ms": sum(durations) / 
len(durations) if durations else 0,\n   624\t            "p99_duration_ms": 
sorted(durations)[int(len(durations) * 0.99)] if len(durations) >= 100 else 0,\n
625\t            "cache_hit_rate": self.cache_hits / (self.cache_hits + 
self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,\n   
626\t            "errors_total": self.errors_total,\n   627\t            
"active_connections": self.active_connections\n   628\t        }\n   629\t\n   
630\t\n   631\t# 
─────────────────────────────────────────────────────────────────────────\n   
632\t# Connection Pool\n   633\t# 
─────────────────────────────────────────────────────────────────────────\n   
634\t\n   635\tclass AsyncConnectionPool:\n   636\t    """\n   637\t    
Async-aware SQLite connection pool.\n   638\t    \n   639\t    SQLite 
connections can\'t be shared across threads, so we use\n   640\t    a pool of 
connections with proper serialization.\n   641\t    """\n   642\t    \n   643\t 
def __init__(self, db_path: str, max_connections: int = 5):\n   644\t        
self.db_path = db_path\n   645\t        self.max_connections = max_connections\n
646\t        self._pool: asyncio.Queue[sqlite3.Connection] = 
asyncio.Queue(maxsize=max_connections)\n   647\t        self._initialized = 
False\n   648\t        self._lock = asyncio.Lock()\n   649\t    \n   650\t    
async def initialize(self):\n   651\t        """Initialize the connection 
pool."""\n   652\t        async with self._lock:\n   653\t            if 
self._initialized:\n   654\t                return\n   655\t            \n   
656\t            for _ in range(self.max_connections):\n   657\t                
conn = sqlite3.connect(\n   658\t                    self.db_path,\n   659\t    
check_same_thread=False,\n   660\t                    timeout=30.0\n   661\t    
)\n   662\t                conn.execute("PRAGMA journal_mode=WAL")\n   663\t    
conn.execute("PRAGMA synchronous=NORMAL")\n   664\t                await 
self._pool.put(conn)\n   665\t            \n   666\t            
self._initialized = True\n   667\t            logger.info("Connection pool 
initialized with %d connections", self.max_connections)\n   668\t    \n   669\t 
@asynccontextmanager\n   670\t    async def acquire(self) -> 
AsyncIterator[sqlite3.Connection]:\n   671\t        """Acquire a connection from
the pool."""\n   672\t        conn = await self._pool.get()\n   673\t        
try:\n   674\t            yield conn\n   675\t        finally:\n   676\t        
await self._pool.put(conn)\n   677\t    \n   678\t    async def close(self):\n  
679\t        """Close all connections."""\n   680\t        while not 
self._pool.empty():\n   681\t            conn = await self._pool.get()\n   682\t
conn.close()\n   683\t\n   684\t\n   685\t# 
─────────────────────────────────────────────────────────────────────────\n   
686\t# Optimized MCP Server\n   687\t# 
─────────────────────────────────────────────────────────────────────────\n   
688\t\n   689\tclass OptimizedMCPServer:\n   690\t    """\n   691\t    
High-performance MCP server for CORTEX.\n   692\t    \n   693\t    Supports 
multiple transports and provides:\n   694\t    - Connection pooling\n   695\t   
- Query caching\n   696\t    - Batch operations\n   697\t    - Comprehensive 
metrics\n   698\t    """\n   699\t    \n   700\t    def __init__(self, config: 
Optional[MCPServerConfig] = None):\n   701\t        self.config = config or 
MCPServerConfig()\n   702\t        self.metrics = MCPMetrics()\n   703\t        
self.pool: Optional[AsyncConnectionPool] = None\n   704\t        self.executor =
ThreadPoolExecutor(max_workers=self.config.max_workers)\n   705\t        \n   
706\t        # Cache for search results\n   707\t        self._query_cache: 
Dict[str, Any] = {}\n   708\t        self._cache_lock = asyncio.Lock()\n   709\t
\n   710\t        # Running flag\n   711\t        self._running = False\n   
712\t    \n   713\t    async def initialize(self):\n   714\t        
"""Initialize the server."""\n   715\t        # Initialize connection pool\n   
716\t        db_path = os.path.expanduser(self.config.db_path)\n   717\t        
self.pool = AsyncConnectionPool(db_path, 
max_connections=self.config.max_workers)\n   718\t        await 
self.pool.initialize()\n   719\t        \n   720\t        # Initialize 
database\n   721\t        from cortex.migrations import run_migrations\n   722\t
async with self.pool.acquire() as conn:\n   723\t            loop = 
asyncio.get_event_loop()\n   724\t            await 
loop.run_in_executor(self.executor, run_migrations, conn)\n   725\t        \n   
726\t        self._running = True\n   727\t        logger.info("Optimized MCP 
server initialized")\n   728\t    \n   729\t    def _get_cache_key(self, prefix:
str, **params) -> str:\n   730\t        """Generate a cache key from 
parameters."""\n   731\t        sorted_params = sorted(params.items())\n   732\t
param_str = json.dumps(sorted_params, sort_keys=True)\n   733\t        return 
f"{prefix}:{hashlib.md5(param_str.encode()).hexdigest()}"\n   734\t    \n   
735\t    async def _cached_query(self, cache_key: str, query_func: Callable, 
*args) -> Any:\n   736\t        """Execute a query with caching."""\n   737\t   
# Check cache\n   738\t        async with self._cache_lock:\n   739\t           
if cache_key in self._query_cache:\n   740\t                
self.metrics.record_request("cache_hit", 0, cached=True)\n   741\t              
return self._query_cache[cache_key]\n   742\t        \n   743\t        # Execute
query\n   744\t        start = time.time()\n   745\t        result = await 
query_func(*args)\n   746\t        duration_ms = (time.time() - start) * 1000\n 
747\t        \n   748\t        # Cache result\n   749\t        if 
len(self._query_cache) < self.config.query_cache_size:\n   750\t            
async with self._cache_lock:\n   751\t                
self._query_cache[cache_key] = result\n   752\t        \n   753\t        return 
result\n   754\t    \n   755\t    # ─── MCP Tool Implementations 
───────────────────────────────────────\n   756\t    \n   757\t    async def 
cortex_store(\n   758\t        self,\n   759\t        project: str,\n   760\t   
content: str,\n   761\t        fact_type: str = "knowledge",\n   762\t        
tags: str = "[]",\n   763\t        source: str = "",\n   764\t        batch: 
bool = False\n   765\t    ) -> dict:\n   766\t        """\n   767\t        Store
a fact (or batch of facts) in CORTEX.\n   768\t        \n   769\t        
Optimizations:\n   770\t        - Batch mode for multiple facts\n   771\t       
- Async execution with connection pooling\n   772\t        """\n   773\t        
from cortex.engine import CortexEngine\n   774\t        \n   775\t        start 
= time.time()\n   776\t        \n   777\t        async with self.pool.acquire() 
as conn:\n   778\t            # Create engine wrapper\n   779\t            
engine = CortexEngine(self.config.db_path, auto_embed=False)\n   780\t          
engine._conn = conn\n   781\t            \n   782\t            try:\n   783\t   
if batch:\n   784\t                    # Parse batch\n   785\t                  
facts = json.loads(content)  # content is JSON array in batch mode\n   786\t    
loop = asyncio.get_event_loop()\n   787\t                    ids = await 
loop.run_in_executor(\n   788\t                        self.executor,\n   789\t 
engine.store_many,\n   790\t                        facts\n   791\t             
)\n   792\t                    result = {\n   793\t                        
"success": True,\n   794\t                        "fact_ids": ids,\n   795\t    
"count": len(ids)\n   796\t                    }\n   797\t                
else:\n   798\t                    # Single fact\n   799\t                    
parsed_tags = json.loads(tags) if tags else []\n   800\t                    loop
= asyncio.get_event_loop()\n   801\t                    fact_id = await 
loop.run_in_executor(\n   802\t                        self.executor,\n   803\t 
engine.store,\n   804\t                        project,\n   805\t               
content,\n   806\t                        fact_type,\n   807\t                  
parsed_tags,\n   808\t                        "stated",\n   809\t               
source or None,\n   810\t                        None,\n   811\t                
None\n   812\t                    )\n   813\t                    result = {\n   
814\t                        "success": True,\n   815\t                        
"fact_id": fact_id\n   816\t                    }\n   817\t                \n   
818\t                # Invalidate relevant caches\n   819\t                async
with self._cache_lock:\n   820\t                    keys_to_remove = [\n   821\t
k for k in self._query_cache.keys()\n   822\t                        if 
k.startswith(f"recall:{project}") or k.startswith(f"search:{project}")\n   823\t
]\n   824\t                    for k in keys_to_remove:\n   825\t               
del self._query_cache[k]\n   826\t                \n   827\t                
duration_ms = (time.time() - start) * 1000\n   828\t                
self.metrics.record_request("cortex_store", duration_ms)\n   829\t              
\n   830\t                return result\n   831\t                \n   832\t     
except Exception as e:\n   833\t                self.metrics.record_error()\n   
834\t                logger.error("Error in cortex_store: %s", e)\n   835\t     
raise\n   836\t    \n   837\t    async def cortex_search(\n   838\t        
self,\n   839\t        query: str,\n   840\t        project: str = "",\n   841\t
top_k: int = 5,\n   842\t        as_of: str = "",\n   843\t        use_cache: 
bool = True\n   844\t    ) -> dict:\n   845\t        """\n   846\t        Search
CORTEX with caching and performance optimizations.\n   847\t        """\n   
848\t        from cortex.engine import CortexEngine\n   849\t        \n   850\t 
cache_key = self._get_cache_key(\n   851\t            "search",\n   852\t       
query=query,\n   853\t            project=project,\n   854\t            
top_k=top_k,\n   855\t            as_of=as_of\n   856\t        )\n   857\t      
\n   858\t        async def _do_search():\n   859\t            async with 
self.pool.acquire() as conn:\n   860\t                engine = 
CortexEngine(self.config.db_path, auto_embed=False)\n   861\t                
engine._conn = conn\n   862\t                \n   863\t                loop = 
asyncio.get_event_loop()\n   864\t                results = await 
loop.run_in_executor(\n   865\t                    self.executor,\n   866\t     
engine.search,\n   867\t                    query,\n   868\t                    
project or None,\n   869\t                    top_k,\n   870\t                  
as_of or None\n   871\t                )\n   872\t                \n   873\t    
return [\n   874\t                    {\n   875\t                        
"fact_id": r.fact_id,\n   876\t                        "project": r.project,\n  
877\t                        "content": r.content[:200] + "..." if 
len(r.content) > 200 else r.content,\n   878\t                        "score": 
r.score,\n   879\t                        "consensus_score": getattr(r, 
\'consensus_score\', 1.0)\n   880\t                    }\n   881\t              
for r in results\n   882\t                ]\n   883\t        \n   884\t        
if use_cache:\n   885\t            results = await self._cached_query(cache_key,
_do_search)\n   886\t        else:\n   887\t            results = await 
_do_search()\n   888\t        \n   889\t        duration_ms = 0  # Tracked in 
_cached_query\n   890\t        self.metrics.record_request("cortex_search", 
duration_ms, cached=use_cache)\n   891\t        \n   892\t        return {\n   
893\t            "results": results,\n   894\t            "count": 
len(results),\n   895\t            "query": query\n   896\t        }\n   897\t  
\n   898\t    async def cortex_recall(\n   899\t        self,\n   900\t        
project: str,\n   901\t        limit: int = 20,\n   902\t        
include_deprecated: bool = False,\n   903\t        use_cache: bool = True\n   
904\t    ) -> dict:\n   905\t        """\n   906\t        Recall project facts 
with caching.\n   907\t        """\n   908\t        cache_key = 
self._get_cache_key(\n   909\t            "recall",\n   910\t            
project=project,\n   911\t            limit=limit,\n   912\t            
include_deprecated=include_deprecated\n   913\t        )\n   914\t        \n   
915\t        async def _do_recall():\n   916\t            from cortex.engine 
import CortexEngine\n   917\t            \n   918\t            async with 
self.pool.acquire() as conn:\n   919\t                engine = 
CortexEngine(self.config.db_path, auto_embed=False)\n   920\t                
engine._conn = conn\n   921\t                \n   922\t                loop = 
asyncio.get_event_loop()\n   923\t                if include_deprecated:\n   
924\t                    facts = await loop.run_in_executor(\n   925\t          
self.executor, engine.history, project\n   926\t                    )\n   927\t 
else:\n   928\t                    facts = await loop.run_in_executor(\n   929\t
self.executor, engine.recall, project, limit\n   930\t                    )\n   
931\t                \n   932\t                return [\n   933\t               
{\n   934\t                        "id": f.id,\n   935\t                        
"content": f.content[:150] + "..." if len(f.content) > 150 else f.content,\n   
936\t                        "type": f.fact_type,\n   937\t                     
"confidence": f.confidence,\n   938\t                        "consensus_score": 
f.consensus_score,\n   939\t                        "tags": f.tags if 
isinstance(f.tags, list) else []\n   940\t                    }\n   941\t       
for f in facts\n   942\t                ]\n   943\t        \n   944\t        if 
use_cache:\n   945\t            facts = await self._cached_query(cache_key, 
_do_recall)\n   946\t        else:\n   947\t            facts = await 
_do_recall()\n   948\t        \n   949\t        return {\n   950\t            
"project": project,\n   951\t            "facts": facts,\n   952\t            
"count": len(facts)\n   953\t        }\n   954\t    \n   955\t    async def 
cortex_vote(\n   956\t        self,\n   957\t        fact_id: int,\n   958\t    
agent: str,\n   959\t        vote: int,\n   960\t        reason: str = ""\n   
961\t    ) -> dict:\n   962\t        """\n   963\t        Cast a consensus vote 
on a fact.\n   964\t        """\n   965\t        from cortex.engine import 
CortexEngine\n   966\t        \n   967\t        start = time.time()\n   968\t   
\n   969\t        async with self.pool.acquire() as conn:\n   970\t            
engine = CortexEngine(self.config.db_path, auto_embed=False)\n   971\t          
engine._conn = conn\n   972\t            \n   973\t            loop = 
asyncio.get_event_loop()\n   974\t            new_score = await 
loop.run_in_executor(\n   975\t                self.executor,\n   976\t         
engine.vote,\n   977\t                fact_id,\n   978\t                agent,\n
979\t                vote\n   980\t            )\n   981\t            \n   982\t
duration_ms = (time.time() - start) * 1000\n   983\t            
self.metrics.record_request("cortex_vote", duration_ms)\n   984\t            \n 
985\t            return {\n   986\t                "fact_id": fact_id,\n   987\t
"agent": agent,\n   988\t                "vote": vote,\n   989\t                
"new_consensus_score": new_score\n   990\t            }\n   991\t    \n   992\t 
async def get_metrics(self) -> dict:\n   993\t        """Return server 
metrics."""\n   994\t        return self.metrics.get_summary()\n   995\t    \n  
996\t    async def health_check(self) -> dict:\n   997\t        """Health check 
endpoint."""\n   998\t        try:\n   999\t            async with 
self.pool.acquire() as conn:\n  1000\t                conn.execute("SELECT 
1")\n',
        message='1000 lines read from file starting from line 1.',
        display=[],
        extras=None
    )
)
ToolCallPart(
    arguments_part=' 
"/Users/borjafernandezangulo/cortex/CORTEX_WAVE4_ROADMAP.md"}'
)
ToolCall(
    type='function',
    id='tool_rvJKmptcIbUXlR3AL7tT5bHf',
    function=FunctionBody(name='Glob', arguments='{"pattern": "cortex'),
    extras=None
)
ToolResult(
    tool_call_id='tool_0KuCT4gdUe8lbTCoegkSP7yz',
    return_value=ToolOk(
        is_error=False,
        output='     1\t# CORTEX V4.0 — Wave 4 Roadmap & Strategic Analysis\n   
2\t\n     3\t**Date:** 2026-02-16  \n     4\t**Version Analyzed:** 4.0.0a1  \n  
5\t**Classification:** Strategic Architecture Document  \n     6\t\n     
7\t---\n     8\t\n     9\t## Executive Summary\n    10\t\n    11\tThis document 
analyzes the current CORTEX V4.0 implementation, focusing on:\n    12\t1. 
**Consensus Layer** — Neural Swarm Consensus with Reputation-Weighted 
evolution\n    13\t2. **NotebookLM Prepper** — Knowledge synthesis pipeline for 
NotebookLM ingestion\n    14\t3. **Contradictions** — Architectural tensions 
between competing requirements\n    15\t4. **Wave 4 Roadmap** — Prioritized next
steps for Sovereign AI readiness\n    16\t\n    17\t---\n    18\t\n    19\t## 1.
Consensus Layer Analysis\n    20\t\n    21\t### 1.1 Current Implementation 
Status\n    22\t\n    23\t| Component | Status | Location |\n    
24\t|-----------|--------|----------|\n    25\t| Base Consensus (v1) | ✅ 
Implemented | `cortex/engine.py:569-626` |\n    26\t| Consensus Votes Table | ✅
Implemented | `cortex/schema.py:122-132` |\n    27\t| RWC Schema (v2) | ✅ 
Implemented | `cortex/schema.py:134-197` |\n    28\t| Agent Registry | ✅ 
Implemented | `cortex/routes/agents.py` |\n    29\t| Vote API (v1) | ✅ 
Implemented | `cortex/routes/facts.py:77-116` |\n    30\t| Vote API (v2) | ⚠️ 
Partial | `cortex/routes/facts.py:119-159` (missing `VoteV2Request` import) |\n 
31\t| Migration 009 (RWC) | ✅ Implemented | `cortex/migrations.py:196-248` |\n 
32\t\n    33\t### 1.2 Implementation Gaps Identified\n    34\t\n    
35\t```python\n    36\t# BUG: facts.py imports VoteV2Request but it\'s not 
imported at the top\n    37\t# Line 122: req: VoteV2Request - but VoteV2Request 
not in imports\n    38\t# Missing: from cortex.models import VoteV2Request\n    
39\t\n    40\t# BUG: Engine method vote_v2() referenced but not implemented\n   
41\t# Line 141: api_state.engine.vote_v2(...) - method doesn\'t exist in 
engine.py\n    42\t```\n    43\t\n    44\t### 1.3 Consensus Architecture 
Comparison\n    45\t\n    46\t```\n    
47\t┌───────────────────────────────────────────────────────────────────────────
──┐\n    48\t│                    CONSENSUS LAYER EVOLUTION                     
│\n    
49\t├───────────────────────────────────────────────────────────────────────────
──┤\n    50\t│                                                                  
│\n    51\t│  V1: LINEAR (Current Active)        V2: REPUTATION-WEIGHTED (Schema
Ready)  │\n    52\t│  ┌─────────────────────────┐        
┌─────────────────────────┐             │\n    53\t│  │ Score = 1.0 + Σ(v)×0.1  
│        │ Score = Σ(v×r×d) / Σ(r) │             │\n    54\t│  │                
│        │                         │             │\n    55\t│  │ • Equal weight 
votes    │        │ • Reputation-weighted   │             │\n    56\t│  │ • 
Simple sum            │        │ • Temporal decay        │             │\n    
57\t│  │ • Fixed thresholds      │        │ • Dynamic thresholds    │           
│\n    58\t│  │ • No agent identity     │        │ • PKI verification      │    
│\n    59\t│  └─────────────────────────┘        └─────────────────────────┘    
│\n    60\t│                                                                    
│\n    61\t│  Status: ACTIVE                     Status: SCHEMA ONLY (Missing 
Engine)    │\n    62\t│                                                         
│\n    
63\t└───────────────────────────────────────────────────────────────────────────
──┘\n    64\t```\n    65\t\n    66\t### 1.4 Critical Vulnerabilities (from 
Security Audit)\n    67\t\n    68\t| Vulnerability | CVSS | Status |\n    
69\t|---------------|------|--------|\n    70\t| CORS Permissive | 5.3 | 🔴 
Unfixed |\n    71\t| SQL Injection (temporal) | 7.5 | 🔴 Unfixed |\n    72\t| 
Path Traversal (export) | 6.5 | 🔴 Unfixed |\n    73\t| Rate Limiting Stub | N/A
| 🟡 Stub only |\n    74\t| API Key in localStorage | N/A | 🟡 Vulnerable |\n   
75\t\n    76\t---\n    77\t\n    78\t## 2. NotebookLM Prepper Analysis\n    
79\t\n    80\t### 2.1 Current Implementation\n    81\t\n    82\t```\n    
83\t┌───────────────────────────────────────────────────────────────────────────
──┐\n    84\t│                  NOTEBOOKLM PREPPER PIPELINE                     
│\n    
85\t├───────────────────────────────────────────────────────────────────────────
──┤\n    86\t│                                                                  
│\n    87\t│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          
│\n    88\t│  │   CORTEX DB  │───▶│  Synthesize  │───▶│  notebooklm/ │          
│\n    89\t│  │  (SQLite)    │    │   Script     │    │  sources/    │          
│\n    90\t│  └──────────────┘    └──────────────┘    └──────────────┘          
│\n    91\t│         │                   │                     │                
│\n    92\t│         ▼                   ▼                     ▼                
│\n    93\t│    facts, entities      pandas              markdown files         
│\n    94\t│    confidence           aggregation         per-project            
│\n    95\t│                                                                    
│\n    96\t│  Script: scripts/synthesize_notebooklm.py                          
│\n    97\t│  Output: notebooklm_sources/{project}_knowledge.md                 
│\n    98\t│                                                                    
│\n    
99\t└───────────────────────────────────────────────────────────────────────────
──┘\n   100\t```\n   101\t\n   102\t### 2.2 Output Format\n   103\t\n   
104\tEach generated file follows this structure:\n   105\t\n   
106\t```markdown\n   107\t# 🧠 CORTEX Domain: {PROJECT}\n   108\t\n   109\t## 🔍
NOTAS DE INVESTIGACIÓN (CRÍTICO)\n   110\t> NotebookLM: He detectado las 
siguientes lagunas en CORTEX para este proyecto.\n   111\t- Hay **{N}** hechos 
sin verificar que requieren validación lógica.\n   112\t- Las siguientes 
entidades carecen de conexiones relacionales: {entities}.\n   113\t\n   114\t## 
Base de Conocimiento\n   115\t### {fact_type}\n   116\t- **{content}** (Confid: 
{confidence})\n   117\t```\n   118\t\n   119\t### 2.3 Current Coverage (from 
filesystem)\n   120\t\n   121\t| Project | Facts Generated | Status |\n   
122\t|---------|-----------------|--------|\n   123\t| cortex | ~30 facts | ✅ 
Active |\n   124\t| moskv-swarm | ~50 facts | ✅ Active |\n   125\t| naroa-web |
~15 facts | ✅ Active |\n   126\t| __system__ | ~20 facts | ✅ Active |\n   
127\t| __bridges__ | ~10 facts | ✅ Active |\n   128\t\n   129\t---\n   130\t\n 
131\t## 3. Contradictions Between Projects\n   132\t\n   133\t### 3.1 
Contradiction Matrix\n   134\t\n   135\t```\n   
136\t┌──────────────────────────────────────────────────────────────────────────
───┐\n   137\t│                    ARCHITECTURAL CONTRADICTIONS                 
│\n   
138\t├──────────────────────────────────────────────────────────────────────────
───┤\n   139\t│                                                                 
│\n   140\t│  C1: SECURITY vs USABILITY                                         
│\n   141\t│  
┌─────────────────────────────────────────────────────────────────────┐   │\n   
142\t│  │ • CORS restrictive breaks Hive UI development                       │ 
│\n   143\t│  │ • PKI signatures add friction to agent onboarding               
│   │\n   144\t│  │ • Rate limiting may throttle legitimate swarm activity      
│   │\n   145\t│  │                                                             
│   │\n   146\t│  │ RESOLUTION: Tiered security model                           
│   │\n   147\t│  │ • Dev mode: permissive CORS, no sigs                        
│   │\n   148\t│  │ • Prod mode: strict CORS, PKI required                      
│   │\n   149\t│  
└─────────────────────────────────────────────────────────────────────┘   │\n   
150\t│                                                                          
│\n   151\t│  C2: CONSENSUS V1 vs V2                                            
│\n   152\t│  
┌─────────────────────────────────────────────────────────────────────┐   │\n   
153\t│  │ • V1 is simple but vulnerable to Sybil attacks                      │ 
│\n   154\t│  │ • V2 is secure but computationally expensive                    
│   │\n   155\t│  │ • Migrating votes changes historical consensus scores       
│   │\n   156\t│  │                                                             
│   │\n   157\t│  │ RESOLUTION: Dual-mode operation                             
│   │\n   158\t│  │ • V1 for human agents (trusted environment)                 
│   │\n   159\t│  │ • V2 for AI agents (untrusted, requires reputation)         
│   │\n   160\t│  
└─────────────────────────────────────────────────────────────────────┘   │\n   
161\t│                                                                          
│\n   162\t│  C3: SYNC DIRECTION                                                
│\n   163\t│  
┌─────────────────────────────────────────────────────────────────────┐   │\n   
164\t│  │ • CORTEX wants to be Source of Truth                                │ 
│\n   165\t│  │ • Legacy ~/.agent/memory/ files still used by external tools    
│   │\n   166\t│  │ • Bidirectional sync creates conflict resolution complexity 
│   │\n   167\t│  │                                                             
│   │\n   168\t│  │ RESOLUTION: Gradual migration                               
│   │\n   169\t│  │ • Phase 1: CORTEX → JSON (write-back)                       
│   │\n   170\t│  │ • Phase 2: JSON read-only, CORTEX write                     
│   │\n   171\t│  │ • Phase 3: Deprecate JSON entirely                          
│   │\n   172\t│  
└─────────────────────────────────────────────────────────────────────┘   │\n   
173\t│                                                                          
│\n   174\t│  C4: TENANT ISOLATION vs CONSENSUS                                 
│\n   175\t│  
┌─────────────────────────────────────────────────────────────────────┐   │\n   
176\t│  │ • Tenant isolation requires per-project facts                       │ 
│\n   177\t│  │ • Consensus works best with cross-tenant visibility             
│   │\n   178\t│  │ • Reputation is global but votes are per-fact               
│   │\n   179\t│  │                                                             
│   │\n   180\t│  │ RESOLUTION: Scoped consensus                                
│   │\n   181\t│  │ • Facts: per-tenant isolated                                
│   │\n   182\t│  │ • Reputation: global across tenants                         
│   │\n   183\t│  │ • Trust edges: tenant-scoped                                
│   │\n   184\t│  
└─────────────────────────────────────────────────────────────────────┘   │\n   
185\t│                                                                          
│\n   186\t│  C5: IMMUTABILITY vs GRAPH EVOLUTION                               
│\n   187\t│  
┌─────────────────────────────────────────────────────────────────────┐   │\n   
188\t│  │ • Transaction ledger is append-only (immutable)                     │ 
│\n   189\t│  │ • Graph entities/relations need updates (mention_count++)       
│   │\n   190\t│  │ • Temporal facts can be deprecated (soft delete)            
│   │\n   191\t│  │                                                             
│   │\n   192\t│  │ RESOLUTION: Different immutability levels                   
│   │\n   193\t│  │ • Ledger: fully immutable                                   
│   │\n   194\t│  │ • Facts: soft-delete only                                   
│   │\n   195\t│  │ • Graph: mutable aggregates                                 
│   │\n   196\t│  
└─────────────────────────────────────────────────────────────────────┘   │\n   
197\t│                                                                          
│\n   
198\t└──────────────────────────────────────────────────────────────────────────
───┘\n   199\t```\n   200\t\n   201\t### 3.2 Resolution Priorities\n   202\t\n  
203\t| Contradiction | Impact | Resolution Strategy |\n   
204\t|---------------|--------|---------------------|\n   205\t| C1: Security vs
Usability | High | Environment-based configuration |\n   206\t| C3: Sync 
Direction | High | Deprecation timeline (3 months) |\n   207\t| C2: V1 vs V2 
Consensus | Medium | Dual-mode with clear boundaries |\n   208\t| C4: Tenant vs 
Consensus | Medium | Global reputation, scoped votes |\n   209\t| C5: 
Immutability vs Graph | Low | Accept different consistency models |\n   210\t\n 
211\t---\n   212\t\n   213\t## 4. Wave 4 Roadmap\n   214\t\n   215\t### 4.1 
Phase Breakdown\n   216\t\n   217\t```\n   
218\t┌──────────────────────────────────────────────────────────────────────────
───┐\n   219\t│                         WAVE 4 ROADMAP                          
│\n   220\t│                    Sovereign AI Readiness                          
│\n   
221\t├──────────────────────────────────────────────────────────────────────────
───┤\n   222\t│                                                                 
│\n   223\t│  SPRINT 1-2: CRITICAL SECURITY (Weeks 1-4)                         
│\n   224\t│  ═════════════════════════════════════════                         
│\n   225\t│  □ Fix CORS configuration (cortex/api.py:80-86)                    
│\n   226\t│  □ Fix SQL injection in temporal filters (search.py:89)            
│\n   227\t│  □ Fix path traversal in export (api.py:302-321)                   
│\n   228\t│  □ Implement rate limiting (Redis or in-memory)                    
│\n   229\t│  □ Add request validation middleware                               
│\n   230\t│                                                                    
│\n   231\t│  DELIVERABLE: Security-hardened API ready for external exposure    
│\n   232\t│                                                                    
│\n   233\t│  SPRINT 3-4: RWC ENGINE (Weeks 5-8)                                
│\n   234\t│  ═══════════════════════════════                                   
│\n   235\t│  □ Implement vote_v2() method in CortexEngine                      
│\n   236\t│  □ Fix VoteV2Request import in facts router                        
│\n   237\t│  □ Implement reputation calculation with EMA                       
│\n   238\t│  □ Add temporal decay to votes                                     
│\n   239\t│  □ Create consensus_outcomes tracking                              
│\n   240\t│  □ Add agent reputation update job                                 
│\n   241\t│                                                                    
│\n   242\t│  DELIVERABLE: Reputation-Weighted Consensus fully operational      
│\n   243\t│                                                                    
│\n   244\t│  SPRINT 5-6: SYNC CONSOLIDATION (Weeks 9-12)                       
│\n   245\t│  ═════════════════════════════════════════                         
│\n   246\t│  □ Deprecate ~/.agent/memory/ write-back                           
│\n   247\t│  □ Make CORTEX DB the exclusive Source of Truth                    
│\n   248\t│  □ Add migration tooling for legacy users                          
│\n   249\t│  □ Update CLI to remove writeback commands                         
│\n   250\t│  □ Add backup/restore functionality                                
│\n   251\t│                                                                    
│\n   252\t│  DELIVERABLE: Single source of truth architecture                  
│\n   253\t│                                                                    
│\n   254\t│  SPRINT 7-8: NOTEBOOKLM ENHANCEMENT (Weeks 13-16)                  
│\n   255\t│  ═══════════════════════════════════════════════                   
│\n   256\t│  □ Add entity relationship graph to exports                        
│\n   257\t│  □ Include consensus scores in NotebookLM output                   
│\n   258\t│  □ Add temporal snapshots ("what we knew at X time")               
│\n   259\t│  □ Create NotebookLM feedback loop (verified facts back to CORTEX) 
│\n   260\t│  □ Add gap analysis automation                                     
│\n   261\t│                                                                    
│\n   262\t│  DELIVERABLE: Bidirectional NotebookLM integration                 
│\n   263\t│                                                                    
│\n   264\t│  SPRINT 9-10: TRUST GRAPH (Weeks 17-20)                            
│\n   265\t│  ═══════════════════════════════════════                           
│\n   266\t│  □ Implement trust_edges operations                                
│\n   267\t│  □ Add EigenTrust-style transitive trust calculation               
│\n   268\t│  □ Create trust delegation UI                                      
│\n   269\t│  □ Add collusion detection (clique analysis)                       
│\n   270\t│  □ Implement trust graph visualization                             
│\n   271\t│                                                                    
│\n   272\t│  DELIVERABLE: Decentralized trust infrastructure                   
│\n   273\t│                                                                    
│\n   274\t│  SPRINT 11-12: SOVEREIGN AI POLISH (Weeks 21-24)                   
│\n   275\t│  ═══════════════════════════════════════════════                   
│\n   276\t│  □ Add cryptographic vote signatures (Ed25519)                     
│\n   277\t│  □ Implement staking mechanism (optional)                          
│\n   278\t│  □ Create governance parameters (DAO-ready)                        
│\n   279\t│  □ Add cross-swarm federation protocol                             
│\n   280\t│  □ Performance optimization (caching, indexing)                    
│\n   281\t│                                                                    
│\n   282\t│  DELIVERABLE: Production-ready Sovereign AI memory                 
│\n   283\t│                                                                    
│\n   
284\t└──────────────────────────────────────────────────────────────────────────
───┘\n   285\t```\n   286\t\n   287\t### 4.2 Detailed Implementation Plan\n   
288\t\n   289\t#### Sprint 1-2: Critical Security Fixes\n   290\t\n   
291\t```python\n   292\t# cortex/api.py - CORS Fix\n   293\tfrom cortex.config 
import ALLOWED_ORIGINS\n   294\t\n   295\tapp.add_middleware(\n   296\t    
CORSMiddleware,\n   297\t    allow_origins=ALLOWED_ORIGINS,  # No more 
wildcard\n   298\t    allow_credentials=True,\n   299\t    allow_methods=["GET",
"POST", "PUT", "DELETE"],\n   300\t    allow_headers=["Authorization", 
"Content-Type"],\n   301\t)\n   302\t\n   303\t# cortex/search.py - SQL 
Injection Fix\n   304\tALLOWED_TEMPORAL_FILTERS = {\n   305\t    "active": 
"valid_until IS NULL",\n   306\t    "deprecated": "valid_until IS NOT NULL",\n  
307\t}\n   308\t\n   309\tdef apply_temporal_filter(sql: str, filter_name: str) 
-> str:\n   310\t    if filter_name not in ALLOWED_TEMPORAL_FILTERS:\n   311\t  
raise ValueError(f"Invalid temporal filter: {filter_name}")\n   312\t    return 
sql + f" AND {ALLOWED_TEMPORAL_FILTERS[filter_name]}"\n   313\t```\n   314\t\n  
315\t#### Sprint 3-4: RWC Engine Implementation\n   316\t\n   317\t```python\n  
318\t# cortex/engine.py - Missing vote_v2 method\n   319\t\n   320\tdef 
vote_v2(\n   321\t    self,\n   322\t    fact_id: int,\n   323\t    agent_id: 
str,\n   324\t    value: int,\n   325\t    reason: Optional[str] = None,\n   
326\t) -> float:\n   327\t    """Cast a reputation-weighted vote (RWC v2)."""\n 
328\t    conn = self._get_conn()\n   329\t    \n   330\t    # 1. Get agent 
reputation\n   331\t    row = conn.execute(\n   332\t        "SELECT 
reputation_score FROM agents WHERE id = ? AND is_active = TRUE",\n   333\t      
(agent_id,)\n   334\t    ).fetchone()\n   335\t    if not row:\n   336\t        
raise ValueError(f"Agent {agent_id} not found or inactive")\n   337\t    \n   
338\t    rep_score = row[0]\n   339\t    vote_weight = rep_score  # Simplified -
could include stake\n   340\t    \n   341\t    # 2. Insert/update vote\n   342\t
conn.execute(\n   343\t        """\n   344\t        INSERT OR REPLACE INTO 
consensus_votes_v2 \n   345\t        (fact_id, agent_id, vote, vote_weight, 
agent_rep_at_vote, created_at)\n   346\t        VALUES (?, ?, ?, ?, ?, 
datetime(\'now\'))\n   347\t        """,\n   348\t        (fact_id, agent_id, 
value, vote_weight, rep_score)\n   349\t    )\n   350\t    \n   351\t    # 3. 
Recalculate with reputation weighting\n   352\t    score = 
self._recalculate_consensus_v2(fact_id, conn)\n   353\t    conn.commit()\n   
354\t    return score\n   355\t\n   356\tdef _recalculate_consensus_v2(self, 
fact_id: int, conn: sqlite3.Connection) -> float:\n   357\t    """Calculate 
reputation-weighted consensus score."""\n   358\t    row = conn.execute(\n   
359\t        """\n   360\t        SELECT \n   361\t            SUM(v.vote * 
v.vote_weight * v.decay_factor) as weighted_sum,\n   362\t            
SUM(v.vote_weight * v.decay_factor) as total_weight\n   363\t        FROM 
consensus_votes_v2 v\n   364\t        JOIN agents a ON v.agent_id = a.id\n   
365\t        WHERE v.fact_id = ? AND a.is_active = TRUE\n   366\t        """,\n 
367\t        (fact_id,)\n   368\t    ).fetchone()\n   369\t    \n   370\t    
weighted_sum = row[0] or 0\n   371\t    total_weight = row[1] or 0\n   372\t    
\n   373\t    if total_weight > 0:\n   374\t        normalized = weighted_sum / 
total_weight  # [-1, 1]\n   375\t        score = 1.0 + normalized  # [0, 2]\n   
376\t    else:\n   377\t        score = 1.0\n   378\t    \n   379\t    # Update 
fact with new score\n   380\t    confidence = 
self._determine_confidence_v2(score, total_weight)\n   381\t    conn.execute(\n 
382\t        "UPDATE facts SET consensus_score = ?, confidence = ? WHERE id = 
?",\n   383\t        (score, confidence, fact_id)\n   384\t    )\n   385\t    \n
386\t    return score\n   387\t```\n   388\t\n   389\t### 4.3 Success Metrics\n 
390\t\n   391\t| Phase | Metric | Target |\n   
392\t|-------|--------|--------|\n   393\t| Security | Vulnerabilities (CVSS > 
5) | 0 |\n   394\t| RWC | Test coverage | > 90% |\n   395\t| Sync | Legacy 
write-back usage | 0% |\n   396\t| NotebookLM | Facts exported | 100% coverage 
|\n   397\t| Trust Graph | Trust edges created | > 100 |\n   398\t| Performance 
| API p99 latency | < 100ms |\n   399\t\n   400\t---\n   401\t\n   402\t## 5. 
Risk Assessment\n   403\t\n   404\t| Risk | Likelihood | Impact | Mitigation |\n
405\t|------|------------|--------|------------|\n   406\t| Security fixes break
existing clients | Medium | High | Gradual rollout with feature flags |\n   
407\t| RWC migration corrupts consensus scores | Low | Critical | Backup before 
migration, idempotent ops |\n   408\t| NotebookLM format changes break ingestion
| Medium | Medium | Versioned output formats |\n   409\t| Trust graph creates 
reputation cartels | Medium | Medium | Collusion detection, diversity 
requirements |\n   410\t| Performance degradation with RWC | Medium | Medium | 
Caching, materialized views |\n   411\t\n   412\t---\n   413\t\n   414\t## 6. 
Conclusion\n   415\t\n   416\tCORTEX V4.0 has a solid foundation with:\n   
417\t- ✅ Complete schema for RWC\n   418\t- ✅ Base consensus layer 
operational\n   419\t- ✅ Tenant isolation working\n   420\t- ✅ Graph memory 
functional\n   421\t- ✅ NotebookLM prepper generating exports\n   422\t\n   
423\t**Critical gaps before Sovereign AI readiness:**\n   424\t1. 🔴 Security 
vulnerabilities must be fixed\n   425\t2. 🔴 RWC engine needs implementation\n  
426\t3. 🟡 Sync architecture needs consolidation\n   427\t4. 🟡 Trust graph 
needs completion\n   428\t\n   429\t**Recommendation:** Proceed with Wave 4 as 
outlined, prioritizing security fixes in Sprint 1-2 to enable safe external 
exposure.\n   430\t\n   431\t---\n   432\t\n   433\t*Generated by Kimi Code CLI 
| CORTEX V4.0 Strategic Analysis*\n',
        message='433 lines read from file starting from line 1. End of file 
reached.',
        display=[],
        extras=None
    )
)
ToolCallPart(arguments_part='/**/*.py"}')
StatusUpdate(
    context_usage=0.025238037109375,
    token_usage=TokenUsage(
        input_other=1752,
        output=124,
        input_cache_read=4864,
        input_cache_creation=0
    ),
    message_id='chatcmpl-HPixOwGTd0EroAYuw689wdvd'
)
ToolResult(
    tool_call_id='tool_rvJKmptcIbUXlR3AL7tT5bHf',
    return_value=ToolOk(
        is_error=False,
        output='cortex/__init__.py\ncortex/api.py\ncortex/api_deps.py\ncortex/ap
i_state.py\ncortex/async_client.py\ncortex/auth.py\ncortex/cli.py\ncortex/client
.py\ncortex/config.py\ncortex/daemon.py\ncortex/daemon_cli.py\ncortex/dashboard.
py\ncortex/embeddings.py\ncortex/engine.py\ncortex/export.py\ncortex/graph.py\nc
ortex/hive.py\ncortex/mcp_server.py\ncortex/metrics.py\ncortex/migrate.py\ncorte
x/migrations.py\ncortex/models.py\ncortex/routes/__init__.py\ncortex/routes/admi
n.py\ncortex/routes/agents.py\ncortex/routes/daemon.py\ncortex/routes/dashboard.
py\ncortex/routes/facts.py\ncortex/routes/search.py\ncortex/routes/timing.py\nco
rtex/schema.py\ncortex/search.py\ncortex/sync.py\ncortex/temporal.py\ncortex/tim
ing.py',
        message='Found 35 matches for pattern `cortex/**/*.py`.',
        display=[],
        extras=None
    )
)
StepBegin(n=2)
TextPart(
    type='text',
    text='Let me continue reading the Wave 5 document and examine the key source
files:'
)
ToolCall(
    type='function',
    id='tool_Csx7COqraEacyxdH6tzB81v4',
    function=FunctionBody(
        name='ReadFile',
        arguments='{"path": 
"/Users/borjafernandezangulo/cortex/WAVE5_PERSISTENCE_DEPLOYMENT.md", 
"line_offset": 1000}'
    ),
    extras=None
)
ToolCall(
    type='function',
    id='tool_khcoF4eBGlU4rDhzIKhoVHXa',
    function=FunctionBody(name='ReadFile', arguments='{"path": "/Users/bor'),
    extras=None
)
ToolResult(
    tool_call_id='tool_Csx7COqraEacyxdH6tzB81v4',
    return_value=ToolOk(
        is_error=False,
        output='  1000\t                conn.execute("SELECT 1")\n  1001\t      
return {"status": "healthy", "database": "connected"}\n  1002\t        except 
Exception as e:\n  1003\t            return {"status": "unhealthy", "error": 
str(e)}\n  1004\t    \n  1005\t    async def close(self):\n  1006\t        
"""Shutdown the server."""\n  1007\t        self._running = False\n  1008\t     
if self.pool:\n  1009\t            await self.pool.close()\n  1010\t        
self.executor.shutdown(wait=True)\n  1011\t\n  1012\t\n  1013\t# 
─────────────────────────────────────────────────────────────────────────\n  
1014\t# Transport Implementations\n  1015\t# 
─────────────────────────────────────────────────────────────────────────\n  
1016\t\n  1017\tasync def run_stdio_server(config: MCPServerConfig):\n  1018\t  
"""Run MCP server with stdio transport."""\n  1019\t    server = 
OptimizedMCPServer(config)\n  1020\t    await server.initialize()\n  1021\t    
\n  1022\t    try:\n  1023\t        # Read from stdin, write to stdout\n  1024\t
while server._running:\n  1025\t            line = await 
asyncio.get_event_loop().run_in_executor(\n  1026\t                None, 
sys.stdin.readline\n  1027\t            )\n  1028\t            \n  1029\t       
if not line:\n  1030\t                break\n  1031\t            \n  1032\t     
try:\n  1033\t                request = json.loads(line.strip())\n  1034\t      
method = request.get("method")\n  1035\t                params = 
request.get("params", {})\n  1036\t                request_id = 
request.get("id")\n  1037\t                \n  1038\t                # Route to 
appropriate handler\n  1039\t                handler = getattr(server, method, 
None)\n  1040\t                if handler:\n  1041\t                    result =
await handler(**params)\n  1042\t                    response = {\n  1043\t     
"jsonrpc": "2.0",\n  1044\t                        "result": result,\n  1045\t  
"id": request_id\n  1046\t                    }\n  1047\t                else:\n
1048\t                    response = {\n  1049\t                        
"jsonrpc": "2.0",\n  1050\t                        "error": {"code": -32601, 
"message": f"Method not found: {method}"},\n  1051\t                        
"id": request_id\n  1052\t                    }\n  1053\t                \n  
1054\t                print(json.dumps(response), flush=True)\n  1055\t         
\n  1056\t            except json.JSONDecodeError as e:\n  1057\t               
print(json.dumps({\n  1058\t                    "jsonrpc": "2.0",\n  1059\t     
"error": {"code": -32700, "message": "Parse error"},\n  1060\t                  
"id": None\n  1061\t                }), flush=True)\n  1062\t            except 
Exception as e:\n  1063\t                print(json.dumps({\n  1064\t           
"jsonrpc": "2.0",\n  1065\t                    "error": {"code": -32603, 
"message": str(e)},\n  1066\t                    "id": request_id if 
\'request_id\' in locals() else None\n  1067\t                }), flush=True)\n 
1068\t                \n  1069\t    finally:\n  1070\t        await 
server.close()\n  1071\t\n  1072\t\n  1073\t# Entry point\n  1074\tif __name__ 
== "__main__":\n  1075\t    import sys\n  1076\t    \n  1077\t    config = 
MCPServerConfig(\n  1078\t        db_path=os.environ.get("CORTEX_DB", 
"~/.cortex/cortex.db"),\n  1079\t        transport="stdio"\n  1080\t    )\n  
1081\t    \n  1082\t    asyncio.run(run_stdio_server(config))\n  1083\t```\n  
1084\t\n  1085\t### 2.4 Performance Benchmarks\n  1086\t\n  1087\t```python\n  
1088\t# tests/benchmark_mcp.py\n  1089\t"""\n  1090\tBenchmark suite for MCP 
server performance.\n  1091\t"""\n  1092\t\n  1093\timport asyncio\n  
1094\timport time\n  1095\timport statistics\n  1096\tfrom cortex.mcp_server_v2 
import OptimizedMCPServer, MCPServerConfig\n  1097\t\n  1098\t\n  1099\tasync 
def benchmark_search():\n  1100\t    """Benchmark search performance with and 
without cache."""\n  1101\t    config = MCPServerConfig(query_cache_size=1000)\n
1102\t    server = OptimizedMCPServer(config)\n  1103\t    await 
server.initialize()\n  1104\t    \n  1105\t    queries = [\n  1106\t        
"machine learning",\n  1107\t        "neural networks",\n  1108\t        "vector
search",\n  1109\t        "consensus algorithm",\n  1110\t        "database 
optimization"\n  1111\t    ] * 20  # 100 total queries\n  1112\t    \n  1113\t  
# Cold cache\n  1114\t    cold_times = []\n  1115\t    for query in 
queries[:10]:\n  1116\t        start = time.time()\n  1117\t        await 
server.cortex_search(query, use_cache=True)\n  1118\t        
cold_times.append((time.time() - start) * 1000)\n  1119\t    \n  1120\t    # 
Warm cache (repeated queries)\n  1121\t    warm_times = []\n  1122\t    for 
query in queries[:10]:  # Same queries\n  1123\t        start = time.time()\n  
1124\t        await server.cortex_search(query, use_cache=True)\n  1125\t       
warm_times.append((time.time() - start) * 1000)\n  1126\t    \n  1127\t    
print(f"Search Performance:")\n  1128\t    print(f"  Cold cache: 
{statistics.mean(cold_times):.2f}ms avg")\n  1129\t    print(f"  Warm cache: 
{statistics.mean(warm_times):.2f}ms avg")\n  1130\t    print(f"  Speedup: 
{statistics.mean(cold_times) / statistics.mean(warm_times):.1f}x")\n  1131\t    
\n  1132\t    await server.close()\n  1133\t\n  1134\t\n  1135\tasync def 
benchmark_batch_store():\n  1136\t    """Benchmark batch store vs individual 
stores."""\n  1137\t    config = MCPServerConfig()\n  1138\t    server = 
OptimizedMCPServer(config)\n  1139\t    await server.initialize()\n  1140\t    
\n  1141\t    # Individual stores\n  1142\t    facts = [\n  1143\t        
{"project": "benchmark", "content": f"Test fact {i}", "fact_type": 
"knowledge"}\n  1144\t        for i in range(100)\n  1145\t    ]\n  1146\t    \n
1147\t    start = time.time()\n  1148\t    for fact in facts:\n  1149\t        
await server.cortex_store(**fact)\n  1150\t    individual_time = (time.time() - 
start) * 1000\n  1151\t    \n  1152\t    # Batch store\n  1153\t    start = 
time.time()\n  1154\t    await server.cortex_store(\n  1155\t        
project="benchmark",\n  1156\t        content=json.dumps(facts),\n  1157\t      
batch=True\n  1158\t    )\n  1159\t    batch_time = (time.time() - start) * 
1000\n  1160\t    \n  1161\t    print(f"\\nStore Performance (100 facts):")\n  
1162\t    print(f"  Individual: {individual_time:.2f}ms 
({individual_time/100:.2f}ms/fact)")\n  1163\t    print(f"  Batch: 
{batch_time:.2f}ms ({batch_time/100:.2f}ms/fact)")\n  1164\t    print(f"  
Speedup: {individual_time / batch_time:.1f}x")\n  1165\t    \n  1166\t    await 
server.close()\n  1167\t\n  1168\t\n  1169\t# Expected Results:\n  1170\t# 
Search Performance:\n  1171\t#   Cold cache: 45.23ms avg\n  1172\t#   Warm 
cache: 0.12ms avg\n  1173\t#   Speedup: 376.9x\n  1174\t#\n  1175\t# Store 
Performance (100 facts):\n  1176\t#   Individual: 2345.67ms (23.46ms/fact)\n  
1177\t#   Batch: 456.78ms (4.57ms/fact)\n  1178\t#   Speedup: 5.1x\n  
1179\t```\n  1180\t\n  1181\t---\n  1182\t\n  1183\t## 3. Deployment Patterns\n 
1184\t\n  1185\t### 3.1 Docker Deployment\n  1186\t\n  1187\t```dockerfile\n  
1188\t# Dockerfile.production\n  1189\tFROM python:3.12-slim\n  1190\t\n  
1191\t# Install system dependencies\n  1192\tRUN apt-get update && apt-get 
install -y \\\n  1193\t    libsqlite3-dev \\\n  1194\t    && rm -rf 
/var/lib/apt/lists/*\n  1195\t\n  1196\t# Set working directory\n  1197\tWORKDIR
/app\n  1198\t\n  1199\t# Install Python dependencies\n  1200\tCOPY 
pyproject.toml .\n  1201\tRUN pip install --no-cache-dir -e ".[all]"\n  1202\t\n
1203\t# Copy application\n  1204\tCOPY cortex/ ./cortex/\n  1205\t\n  1206\t# 
Create non-root user\n  1207\tRUN useradd -m -u 1000 cortex && \\\n  1208\t    
mkdir -p /data && \\\n  1209\t    chown -R cortex:cortex /data\n  1210\t\n  
1211\t# Environment\n  1212\tENV CORTEX_DB=/data/cortex.db\n  1213\tENV 
CORTEX_ALLOWED_ORIGINS=http://localhost:3000\n  1214\tENV PYTHONUNBUFFERED=1\n  
1215\t\n  1216\tUSER cortex\n  1217\t\n  1218\t# Expose ports\n  1219\tEXPOSE 
8484 9999\n  1220\t\n  1221\t# Health check\n  1222\tHEALTHCHECK --interval=30s 
--timeout=5s --start-period=5s --retries=3 \\\n  1223\t    CMD python -c "import
requests; requests.get(\'http://localhost:8484/health\')" || exit 1\n  1224\t\n 
1225\t# Default: run API server\n  1226\tCMD ["uvicorn", "cortex.api:app", 
"--host", "0.0.0.0", "--port", "8484"]\n  1227\t```\n  1228\t\n  1229\t```yaml\n
1230\t# docker-compose.yml\n  1231\tversion: "3.8"\n  1232\t\n  
1233\tservices:\n  1234\t  cortex-api:\n  1235\t    build:\n  1236\t      
context: .\n  1237\t      dockerfile: Dockerfile.production\n  1238\t    
ports:\n  1239\t      - "8484:8484"\n  1240\t    volumes:\n  1241\t      - 
cortex-data:/data\n  1242\t    environment:\n  1243\t      - 
CORTEX_DB=/data/cortex.db\n  1244\t      - CORTEX_RATE_LIMIT=1000\n  1245\t    
restart: unless-stopped\n  1246\t    \n  1247\t  cortex-mcp:\n  1248\t    
build:\n  1249\t      context: .\n  1250\t      dockerfile: 
Dockerfile.production\n  1251\t    command: ["python", "-m", 
"cortex.mcp_server_v2"]\n  1252\t    volumes:\n  1253\t      - 
cortex-data:/data\n  1254\t    environment:\n  1255\t      - 
CORTEX_DB=/data/cortex.db\n  1256\t    restart: unless-stopped\n  1257\t    \n  
1258\t  # Optional: Prometheus metrics\n  1259\t  prometheus:\n  1260\t    
image: prom/prometheus\n  1261\t    volumes:\n  1262\t      - 
./prometheus.yml:/etc/prometheus/prometheus.yml\n  1263\t    ports:\n  1264\t   
- "9090:9090"\n  1265\t\n  1266\tvolumes:\n  1267\t  cortex-data:\n  1268\t```\n
1269\t\n  1270\t### 3.2 systemd Service\n  1271\t\n  1272\t```ini\n  1273\t# 
deploy/cortex.service\n  1274\t[Unit]\n  1275\tDescription=CORTEX Sovereign 
Memory API\n  1276\tAfter=network.target\n  1277\t\n  1278\t[Service]\n  
1279\tType=simple\n  1280\tUser=cortex\n  1281\tGroup=cortex\n  
1282\tWorkingDirectory=/opt/cortex\n  
1283\tEnvironment=CORTEX_DB=/var/lib/cortex/cortex.db\n  
1284\tEnvironment=CORTEX_ALLOWED_ORIGINS=http://localhost:3000\n  
1285\tEnvironment=PYTHONUNBUFFERED=1\n  
1286\tExecStart=/opt/cortex/venv/bin/uvicorn cortex.api:app --host 127.0.0.1 
--port 8484\n  1287\tRestart=always\n  1288\tRestartSec=5\n  1289\t\n  1290\t# 
Security hardening\n  1291\tNoNewPrivileges=true\n  1292\tPrivateTmp=true\n  
1293\tProtectSystem=strict\n  1294\tProtectHome=true\n  
1295\tReadWritePaths=/var/lib/cortex\n  1296\t\n  1297\t[Install]\n  
1298\tWantedBy=multi-user.target\n  1299\t```\n  1300\t\n  1301\t### 3.3 
Kubernetes Deployment\n  1302\t\n  1303\t```yaml\n  1304\t# 
deploy/k8s-deployment.yaml\n  1305\tapiVersion: apps/v1\n  1306\tkind: 
Deployment\n  1307\tmetadata:\n  1308\t  name: cortex\n  1309\t  labels:\n  
1310\t    app: cortex\n  1311\tspec:\n  1312\t  replicas: 3\n  1313\t  
selector:\n  1314\t    matchLabels:\n  1315\t      app: cortex\n  1316\t  
template:\n  1317\t    metadata:\n  1318\t      labels:\n  1319\t        app: 
cortex\n  1320\t    spec:\n  1321\t      containers:\n  1322\t      - name: 
cortex\n  1323\t        image: cortex:v4.1.0\n  1324\t        ports:\n  1325\t  
- containerPort: 8484\n  1326\t          name: api\n  1327\t        - 
containerPort: 9999\n  1328\t          name: mcp\n  1329\t        env:\n  1330\t
- name: CORTEX_DB\n  1331\t          value: "/data/cortex.db"\n  1332\t        
volumeMounts:\n  1333\t        - name: data\n  1334\t          mountPath: 
/data\n  1335\t        livenessProbe:\n  1336\t          httpGet:\n  1337\t     
path: /health\n  1338\t            port: 8484\n  1339\t          
initialDelaySeconds: 10\n  1340\t          periodSeconds: 30\n  1341\t        
readinessProbe:\n  1342\t          httpGet:\n  1343\t            path: /health\n
1344\t            port: 8484\n  1345\t          initialDelaySeconds: 5\n  1346\t
periodSeconds: 5\n  1347\t      volumes:\n  1348\t      - name: data\n  1349\t  
persistentVolumeClaim:\n  1350\t          claimName: cortex-data\n  1351\t---\n 
1352\tapiVersion: v1\n  1353\tkind: Service\n  1354\tmetadata:\n  1355\t  name: 
cortex\n  1356\tspec:\n  1357\t  selector:\n  1358\t    app: cortex\n  1359\t  
ports:\n  1360\t  - port: 8484\n  1361\t    targetPort: 8484\n  1362\t    name: 
api\n  1363\t  - port: 9999\n  1364\t    targetPort: 9999\n  1365\t    name: 
mcp\n  1366\t  type: ClusterIP\n  1367\t```\n  1368\t\n  1369\t---\n  1370\t\n  
1371\t## 4. Migration Plan\n  1372\t\n  1373\t### 4.1 Wave 5 Timeline\n  
1374\t\n  1375\t```\n  1376\tWeek 1-2: Immutable Ledger\n  1377\t├── Migration 
009: Merkle tree schema\n  1378\t├── Implementation: MerkleTree class\n  
1379\t├── CLI: ledger checkpoint, verify, export\n  1380\t└── Tests: 95% 
coverage\n  1381\t\n  1382\tWeek 3-4: MCP Optimization\n  1383\t├── 
mcp_server_v2.py implementation\n  1384\t├── Connection pooling\n  1385\t├── 
Caching layer\n  1386\t├── Batch operations\n  1387\t└── Benchmark suite\n  
1388\t\n  1389\tWeek 5: Deployment\n  1390\t├── Dockerfile.production\n  
1391\t├── docker-compose.yml\n  1392\t├── systemd service\n  1393\t├── 
Kubernetes manifests\n  1394\t└── Documentation\n  1395\t\n  1396\tWeek 6: 
Integration & Testing\n  1397\t├── End-to-end tests\n  1398\t├── Performance 
validation\n  1399\t├── Security audit\n  1400\t└── Release candidate\n  
1401\t```\n  1402\t\n  1403\t### 4.2 Migration Commands\n  1404\t\n  
1405\t```bash\n  1406\t# Upgrade to Wave 5\n  1407\tcortex migrate\n  1408\t\n  
1409\t# Create first Merkle checkpoint\n  1410\tcortex ledger checkpoint\n  
1411\t\n  1412\t# Verify integrity\n  1413\tcortex ledger verify\n  1414\t\n  
1415\t# Start optimized MCP server\n  1416\tcortex mcp start --transport sse 
--port 9999\n  1417\t\n  1418\t# Run benchmarks\n  1419\tcortex benchmark 
--suite all\n  1420\t```\n  1421\t\n  1422\t---\n  1423\t\n  1424\t## 5. Success
Criteria\n  1425\t\n  1426\t| Metric | Target | Measurement |\n  
1427\t|--------|--------|-------------|\n  1428\t| Ledger Verification | <100ms 
for 10k TX | `cortex ledger verify` |\n  1429\t| MCP Cold Query | <50ms | 
Benchmark suite |\n  1430\t| MCP Warm Query | <1ms | Benchmark suite |\n  
1431\t| MCP Throughput | >1000 req/sec | Load test |\n  1432\t| Cache Hit Rate |
>80% | Runtime metrics |\n  1433\t| Docker Image Size | <200MB | `docker images`
|\n  1434\t| Memory Usage | <512MB | Container metrics |\n  1435\t\n  
1436\t---\n  1437\t\n  1438\t## Appendix A: API Changes\n  1439\t\n  1440\t### 
New Endpoints\n  1441\t\n  1442\t```\n  1443\tPOST   /v1/ledger/checkpoint      
# Create Merkle checkpoint\n  1444\tGET    /v1/ledger/verify          # Verify 
integrity\n  1445\tPOST   /v1/ledger/export          # Export verifiable log\n  
1446\tGET    /v1/mcp/metrics            # MCP server metrics\n  1447\tGET    
/v1/mcp/health             # Health check\n  1448\t```\n  1449\t\n  1450\t### 
New CLI Commands\n  1451\t\n  1452\t```\n  1453\tcortex ledger checkpoint       
# Create checkpoint\n  1454\tcortex ledger verify              # Verify 
integrity\n  1455\tcortex ledger export              # Export log\n  
1456\tcortex mcp start                  # Start MCP server\n  1457\tcortex 
benchmark                  # Run benchmarks\n  1458\t```\n  1459\t\n  
1460\t---\n  1461\t\n  1462\t**End of Wave 5 Proposal**\n  1463\t\n  
1464\t*Prepared for CORTEX V4.0 Architecture Review*\n',
        message='465 lines read from file starting from line 1000. End of file 
reached.',
        display=[],
        extras=None
    )
)
ToolCallPart(arguments_part='jafernandezangulo/cortex/cortex/engine.py"}')
ToolCall(
    type='function',
    id='tool_wPLABfBAoxlTT38ZdDj48ymR',
    function=FunctionBody(name='ReadFile', arguments='{"path": "/Users/b'),
    extras=None
)
ToolResult(
    tool_call_id='tool_khcoF4eBGlU4rDhzIKhoVHXa',
    return_value=ToolOk(
        is_error=False,
        output='     1\t"""\n     2\tCORTEX v4.0 — Core Engine.\n     3\t\n     
4\tThe sovereign memory engine. Manages facts, embeddings, temporal queries,\n  
5\tand the transaction ledger. Single SQLite database, zero network deps.\n     
6\t"""\n     7\t\n     8\tfrom __future__ import annotations\n     9\t\n    
10\timport hashlib\n    11\timport json\n    12\timport logging\n    13\timport 
sqlite3\n    14\tfrom dataclasses import dataclass\n    15\tfrom pathlib import 
Path\n    16\tfrom typing import Optional\n    17\t\n    18\timport sqlite_vec\n
19\t\n    20\tfrom cortex.embeddings import LocalEmbedder\n    21\tfrom 
cortex.embeddings import LocalEmbedder\n    22\tfrom cortex.schema import 
get_init_meta\n    23\tfrom cortex.migrations import run_migrations\n    
24\tfrom cortex.search import SearchResult, semantic_search, text_search\n    
25\tfrom cortex.graph import get_graph, query_entity\n    26\tfrom 
cortex.temporal import build_temporal_filter_params, now_iso\n    27\t\n    
28\tlogger = logging.getLogger("cortex")\n    29\t\n    30\tfrom cortex.config 
import DEFAULT_DB_PATH\n    31\t\n    32\t\n    33\t@dataclass\n    34\tclass 
Fact:\n    35\t    """A single fact stored in CORTEX."""\n    36\t\n    37\t    
id: int\n    38\t    project: str\n    39\t    content: str\n    40\t    
fact_type: str\n    41\t    tags: list[str]\n    42\t    confidence: str\n    
43\t    valid_from: str\n    44\t    valid_until: Optional[str]\n    45\t    
source: Optional[str]\n    46\t    meta: dict\n    47\t    consensus_score: 
float = 1.0\n    48\t\n    49\t    def is_active(self) -> bool:\n    50\t       
return self.valid_until is None\n    51\t\n    52\t    def to_dict(self) -> 
dict:\n    53\t        return {\n    54\t            "id": self.id,\n    55\t   
"project": self.project,\n    56\t            "content": self.content,\n    57\t
"type": self.fact_type,\n    58\t            "tags": self.tags,\n    59\t       
"confidence": self.confidence,\n    60\t            "valid_from": 
self.valid_from,\n    61\t            "valid_until": self.valid_until,\n    62\t
"source": self.source,\n    63\t            "active": self.is_active(),\n    
64\t            "consensus_score": self.consensus_score,\n    65\t        }\n   
66\t\n    67\t\n    68\tclass CortexEngine:\n    69\t    """The Sovereign Ledger
for AI Agents.\n    70\t\n    71\t    Core engine providing:\n    72\t    - 
Semantic vector search (sqlite-vec)\n    73\t    - Temporal fact management 
(valid_from/valid_until)\n    74\t    - Project-scoped isolation\n    75\t    - 
Append-only transaction ledger\n    76\t\n    77\t    Usage:\n    78\t        
engine = CortexEngine()\n    79\t        engine.store("naroa-web", "Uses vanilla
JS, no framework")\n    80\t        results = engine.search("what framework does
naroa use?")\n    81\t    """\n    82\t\n    83\t    def __init__(\n    84\t    
self,\n    85\t        db_path: str | Path = DEFAULT_DB_PATH,\n    86\t        
auto_embed: bool = True,\n    87\t    ):\n    88\t        """Initialize or open 
CORTEX database.\n    89\t\n    90\t        Args:\n    91\t            db_path: 
Path to SQLite database file.\n    92\t            auto_embed: Whether to 
auto-generate embeddings on store.\n    93\t        """\n    94\t        
self._db_path = Path(db_path).expanduser()\n    95\t        
self._db_path.parent.mkdir(parents=True, exist_ok=True)\n    96\t        
self._auto_embed = auto_embed\n    97\t        self._embedder: 
Optional[LocalEmbedder] = None\n    98\t        self._conn: 
Optional[sqlite3.Connection] = None\n    99\t        self._vec_available = 
False\n   100\t\n   101\t    # ─── Connection Management 
────────────────────────────────────\n   102\t\n   103\t    def _get_conn(self) 
-> sqlite3.Connection:\n   104\t        """Get or create SQLite connection with 
vec0 extension."""\n   105\t        if self._conn is not None:\n   106\t        
return self._conn\n   107\t\n   108\t        self._conn = sqlite3.connect(\n   
109\t            str(self._db_path), timeout=10, check_same_thread=False\n   
110\t        )\n   111\t\n   112\t        # Load sqlite-vec extension — handles 
both standard and restricted builds\n   113\t        try:\n   114\t            
if hasattr(self._conn, \'enable_load_extension\'):\n   115\t                
self._conn.enable_load_extension(True)\n   116\t            
sqlite_vec.load(self._conn)\n   117\t            if hasattr(self._conn, 
\'enable_load_extension\'):\n   118\t                
self._conn.enable_load_extension(False)\n   119\t            self._vec_available
= True\n   120\t        except (OSError, AttributeError) as e:\n   121\t        
logger.warning("sqlite-vec not available: %s. Vector search disabled.", e)\n   
122\t            self._vec_available = False\n   123\t\n   124\t        # 
Performance pragmas\n   125\t        self._conn.execute("PRAGMA 
journal_mode=WAL")\n   126\t        self._conn.execute("PRAGMA 
synchronous=NORMAL")\n   127\t        self._conn.execute("PRAGMA 
foreign_keys=ON")\n   128\t\n   129\t        return self._conn\n   130\t\n   
131\t    def get_connection(self) -> sqlite3.Connection:\n   132\t        
"""Public alias for _get_conn (backward compatibility)."""\n   133\t        
return self._get_conn()\n   134\t\n   135\t    def _get_embedder(self) -> 
LocalEmbedder:\n   136\t        """Get or create local embedder (lazy 
load)."""\n   137\t        if self._embedder is None:\n   138\t            
self._embedder = LocalEmbedder()\n   139\t        return self._embedder\n   
140\t\n   141\t    # ─── Database Initialization 
──────────────────────────────────\n   142\t\n   143\t    def init_db(self) -> 
None:\n   144\t        """Initialize database schema using migrations. Safe to 
call multiple times."""\n   145\t        from cortex.schema import ALL_SCHEMA, 
get_init_meta\n   146\t        conn = self._get_conn()\n   147\t        \n   
148\t        # 1. Initialize base schema if not existing\n   149\t        for 
stmt in ALL_SCHEMA:\n   150\t            # Skip vector tables if extension is 
not loaded\n   151\t            if "USING vec0" in stmt and not 
self._vec_available:\n   152\t                continue\n   153\t            
conn.executescript(stmt)\n   154\t        conn.commit()\n   155\t        \n   
156\t        # 2. Run migrations (creates/updates tables)\n   157\t        
run_migrations(conn)\n   158\t\n   159\t        # 3. Insert metadata if not 
exists\n   160\t        for key, value in get_init_meta():\n   161\t            
conn.execute(\n   162\t                "INSERT OR IGNORE INTO cortex_meta (key, 
value) VALUES (?, ?)",\n   163\t                (key, value),\n   164\t         
)\n   165\t\n   166\t        conn.commit()\n   167\t        logger.info("CORTEX 
database initialized (schema + migrated) at %s", self._db_path)\n   168\t\n   
169\t    # ─── Store ────────────────────────────────────────────────────\n   
170\t\n   171\t    def store(\n   172\t        self,\n   173\t        project: 
str,\n   174\t        content: str,\n   175\t        fact_type: str = 
"knowledge",\n   176\t        tags: Optional[list[str]] = None,\n   177\t       
confidence: str = "stated",\n   178\t        source: Optional[str] = None,\n   
179\t        meta: Optional[dict] = None,\n   180\t        valid_from: 
Optional[str] = None,\n   181\t        commit: bool = True,\n   182\t    ) -> 
int:\n   183\t        """Store a fact with automatic embedding and temporal 
metadata.\n   184\t\n   185\t        Args:\n   186\t            project: 
Project/tenant scope.\n   187\t            content: The fact content.\n   188\t 
fact_type: Type (knowledge, decision, error, bridge, ghost).\n   189\t          
tags: Optional list of tags.\n   190\t            confidence: Confidence level 
(stated, verified, hypothesis, deprecated).\n   191\t            source: Where 
the fact came from.\n   192\t            meta: Additional metadata dict.\n   
193\t            valid_from: When fact became valid (default: now).\n   194\t   
commit: Whether to commit the transaction (False for batch ops).\n   195\t\n   
196\t        Returns:\n   197\t            The fact ID.\n   198\t        """\n  
199\t        if not project or not project.strip():\n   200\t            raise 
ValueError("project cannot be empty")\n   201\t        if not content or not 
content.strip():\n   202\t            raise ValueError("content cannot be 
empty")\n   203\t\n   204\t        conn = self._get_conn()\n   205\t        ts =
valid_from or now_iso()\n   206\t        tags_json = json.dumps(tags or [])\n   
207\t        meta_json = json.dumps(meta or {})\n   208\t\n   209\t        
cursor = conn.execute(\n   210\t            """\n   211\t            INSERT INTO
facts (project, content, fact_type, tags, confidence,\n   212\t                 
valid_from, source, meta, created_at, updated_at)\n   213\t            VALUES 
(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\n   214\t            """,\n   215\t            
(project, content, fact_type, tags_json, confidence,\n   216\t             ts, 
source, meta_json, ts, ts),\n   217\t        )\n   218\t        fact_id = 
cursor.lastrowid\n   219\t\n   220\t        # Auto-embed (only if vec0 
available)\n   221\t        if self._auto_embed and self._vec_available:\n   
222\t            try:\n   223\t                embedder = self._get_embedder()\n
224\t                embedding = embedder.embed(content)\n   225\t              
embedding_json = json.dumps(embedding)\n   226\t                conn.execute(\n 
227\t                    "INSERT INTO fact_embeddings (fact_id, embedding) 
VALUES (?, ?)",\n   228\t                    (fact_id, embedding_json),\n   
229\t                )\n   230\t            except (ValueError, sqlite3.Error) 
as e:\n   231\t                logger.warning("Embedding failed for fact %d: 
%s", fact_id, e)\n   232\t        \n   233\t        # Auto-extract Graph 
Entities & Relationships\n   234\t        from cortex.graph import 
process_fact_graph\n   235\t        try:\n   236\t            
process_fact_graph(conn, fact_id, content, project, ts)\n   237\t        except 
Exception as e:\n   238\t            logger.warning("Graph extraction failed for
fact %d: %s", fact_id, e)\n   239\t\n   240\t        # Log transaction\n   241\t
self._log_transaction(conn, project, "store", {\n   242\t            "fact_id": 
fact_id,\n   243\t            "fact_type": fact_type,\n   244\t            
"content_preview": content[:100],\n   245\t        })\n   246\t\n   247\t       
if commit:\n   248\t            conn.commit()\n   249\t            
logger.info("Stored fact #%d in project \'%s\'", fact_id, project)\n   250\t    
return fact_id\n   251\t\n   252\t    def store_many(self, facts: list[dict]) ->
list[int]:\n   253\t        """Store multiple facts in a single transaction 
(Atomic)."""\n   254\t        if not facts:\n   255\t            raise 
ValueError("Cannot store empty list of facts")\n   256\t\n   257\t        conn =
self._get_conn()\n   258\t        ids = []\n   259\t        try:\n   260\t      
with conn: # Handles BEGIN/COMMIT/ROLLBACK automatically\n   261\t              
for f in facts:\n   262\t                    if "project" not in f or not 
f["project"] or not str(f["project"]).strip():\n   263\t                        
raise ValueError("Fact must have project")\n   264\t                    if 
"content" not in f or not f["content"] or not str(f["content"]).strip():\n   
265\t                        raise ValueError("Fact must have content")\n   
266\t                        \n   267\t                    fid = self.store(\n  
268\t                        project=f["project"],\n   269\t                    
content=f["content"],\n   270\t                        
fact_type=f.get("fact_type", "knowledge"),\n   271\t                        
tags=f.get("tags", []),\n   272\t                        
confidence=f.get("confidence", "stated"),\n   273\t                        
source=f.get("source", None),\n   274\t                        
meta=f.get("meta", None),\n   275\t                        
valid_from=f.get("valid_from", None),\n   276\t                        
commit=False, # Don\'t commit inside the loop\n   277\t                    )\n  
278\t                    ids.append(fid)\n   279\t            logger.info("Batch
stored %d facts", len(ids))\n   280\t            return ids\n   281\t        
except Exception as e:\n   282\t            logger.error("Batch store failed: 
%s", e)\n   283\t            raise\n   284\t\n   285\t    def update(\n   286\t 
self,\n   287\t        fact_id: int,\n   288\t        content: Optional[str] = 
None,\n   289\t        tags: Optional[list[str]] = None,\n   290\t        meta: 
Optional[dict] = None,\n   291\t    ) -> int:\n   292\t        """Update a fact 
by deprecating the old one and creating a new one.\n   293\t\n   294\t        
Args:\n   295\t            fact_id: ID of the fact to update.\n   296\t         
content: New content (optional).\n   297\t            tags: New tags 
(optional).\n   298\t            meta: New metadata (optional).\n   299\t\n   
300\t        Returns:\n   301\t            The ID of the new fact.\n   302\t    
"""\n   303\t        if fact_id <= 0:\n   304\t            raise 
ValueError("Invalid fact ID")\n   305\t\n   306\t        conn = 
self._get_conn()\n   307\t        row = conn.execute(\n   308\t            
"SELECT project, content, fact_type, tags, confidence, source, meta FROM facts 
WHERE id = ? AND valid_until IS NULL",\n   309\t            (fact_id,),\n   
310\t        ).fetchone()\n   311\t\n   312\t        if not row:\n   313\t      
raise ValueError(f"Fact {fact_id} not found or inactive")\n   314\t\n   315\t   
project, old_content, fact_type, old_tags_json, confidence, source, 
old_meta_json = row\n   316\t        \n   317\t        # Parse old values 
safely\n   318\t        try:\n   319\t            old_tags = 
json.loads(old_tags_json) if old_tags_json else []\n   320\t        except 
(json.JSONDecodeError, TypeError):\n   321\t            old_tags = []\n   322\t 
\n   323\t        try:\n   324\t            old_meta = json.loads(old_meta_json)
if old_meta_json else {}\n   325\t        except (json.JSONDecodeError, 
TypeError):\n   326\t            old_meta = {}\n   327\t\n   328\t        # 
Prepare new values\n   329\t        new_content = content if content is not None
else old_content\n   330\t        new_tags = tags if tags is not None else 
old_tags\n   331\t        new_meta = old_meta.copy()\n   332\t        if meta:\n
333\t            new_meta.update(meta)\n   334\t            \n   335\t        
new_meta["previous_fact_id"] = fact_id\n   336\t        \n   337\t        # 
Store as new fact\n   338\t        new_id = self.store(\n   339\t            
project=project,\n   340\t            content=new_content,\n   341\t            
fact_type=fact_type,\n   342\t            tags=new_tags,\n   343\t            
confidence=confidence,\n   344\t            source=source,\n   345\t            
meta=new_meta,\n   346\t        )\n   347\t\n   348\t        # Deprecate old 
fact\n   349\t        self.deprecate(fact_id, reason=f"updated_by_{new_id}")\n  
350\t        \n   351\t        return new_id\n   352\t\n   353\t    # ─── Graph 
────────────────────────────────────────────────────\n   354\t\n   355\t    def 
graph(self, project: Optional[str] = None, limit: int = 50) -> dict:\n   356\t  
"""Get knowledge graph (entities and relationships)."""\n   357\t        conn = 
self._get_conn()\n   358\t        return get_graph(conn, project, limit)\n   
359\t\n   360\t    def query_entity(self, name: str, project: Optional[str] = 
None) -> Optional[dict]:\n   361\t        """Query specific entity in the 
graph."""\n   362\t        conn = self._get_conn()\n   363\t        return 
query_entity(conn, name, project)\n   364\t\n   365\t    # ─── Search 
───────────────────────────────────────────────────\n   366\t\n   367\t    def 
search(\n   368\t        self,\n   369\t        query: str,\n   370\t        
project: Optional[str] = None,\n   371\t        top_k: int = 5,\n   372\t       
as_of: Optional[str] = None,\n   373\t        **kwargs,\n   374\t    ) -> 
list[SearchResult]:\n   375\t        """Semantic search across facts.\n   
376\t\n   377\t        Args:\n   378\t            query: Natural language 
query.\n   379\t            project: Optional project scope.\n   380\t          
top_k: Number of results.\n   381\t            as_of: Optional temporal filter 
(ISO 8601).\n   382\t\n   383\t        Returns:\n   384\t            List of 
SearchResult ordered by relevance.\n   385\t        """\n   386\t        if not 
query or not query.strip():\n   387\t            raise ValueError("query cannot 
be empty")\n   388\t            \n   389\t        conn = self._get_conn()\n   
390\t\n   391\t        # Try semantic search first\n   392\t        try:\n   
393\t            embedder = self._get_embedder()\n   394\t            
query_embedding = embedder.embed(query)\n   395\t            results = 
semantic_search(\n   396\t                conn, query_embedding, top_k, project,
as_of\n   397\t            )\n   398\t            if results:\n   399\t         
return results\n   400\t        except (ValueError, RuntimeError, sqlite3.Error)
as e:\n   401\t            logger.warning("Semantic search failed, falling back 
to text: %s", e)\n   402\t\n   403\t        # Fallback to text search\n   404\t 
return text_search(\n   405\t            conn, query, project, limit=top_k, 
fact_type=kwargs.get("fact_type"), tags=kwargs.get("tags")\n   406\t        )\n 
407\t\n   408\t    # ─── Recall (Project Context) 
─────────────────────────────────\n   409\t\n   410\t    def recall(\n   411\t  
self,\n   412\t        project: str,\n   413\t        limit: Optional[int] = 
None,\n   414\t        offset: int = 0,\n   415\t    ) -> list[Fact]:\n   416\t 
"""Load all active facts for a project.\n   417\t\n   418\t        Args:\n   
419\t            project: Project identifier.\n   420\t            limit: Max 
facts to return.\n   421\t            offset: Pagination offset.\n   422\t      
Returns:\n   423\t            List of active Facts for the project.\n   424\t   
"""\n   425\t        conn = self._get_conn()\n   426\t        query = """\n   
427\t            SELECT id, project, content, fact_type, tags, confidence,\n   
428\t                   valid_from, valid_until, source, meta, consensus_score\n
429\t            FROM facts\n   430\t            WHERE project = ? AND 
valid_until IS NULL\n   431\t            ORDER BY \n   432\t                
(consensus_score * 0.8 + (1.0 / (1.0 + (julianday(\'now\') - 
julianday(created_at)))) * 0.2) DESC,\n   433\t                fact_type, \n   
434\t                created_at DESC\n   435\t        """\n   436\t        
params = [project]\n   437\t        if limit:\n   438\t            query += " 
LIMIT ?"\n   439\t            params.append(limit)\n   440\t\n   441\t        if
offset:\n   442\t            query += " OFFSET ?"\n   443\t            
params.append(offset)\n   444\t\n   445\t        cursor = conn.execute(query, 
params)\n   446\t\n   447\t        return [self._row_to_fact(row) for row in 
cursor.fetchall()]\n   448\t\n   449\t    def _verify_fact_tenant(self, fact_id:
int, tenant_id: str) -> bool:\n   450\t        """Lightweight check for fact 
tenant ownership."""\n   451\t        conn = self._get_conn()\n   452\t        
row = conn.execute("SELECT project FROM facts WHERE id = ?", 
(fact_id,)).fetchone()\n   453\t        return row is not None and row[0] == 
tenant_id\n   454\t\n   455\t    def vote(self, fact_id: int, agent: str, value:
int, agent_id: Optional[str] = None) -> float:\n   456\t        """Cast a 
consensus vote on a fact.\n   457\t\n   458\t        Args:\n   459\t            
fact_id: The ID of the fact to vote on.\n   460\t            agent: The name of 
the agent voting (legacy).\n   461\t            value: Vote value (1 for verify,
-1 for dispute, 0 to remove).\n   462\t            agent_id: The UUID of the 
agent (RWC v2). If provided, uses RWC logic.\n   463\t\n   464\t        
Returns:\n   465\t            The updated consensus_score.\n   466\t        
"""\n   467\t        if agent_id:\n   468\t            return 
self.vote_v2(fact_id, agent_id, value)\n   469\t\n   470\t        # Legacy 
fallback\n   471\t        conn = self._get_conn()\n   472\t        if value == 
0:\n   473\t            conn.execute(\n   474\t                "DELETE FROM 
consensus_votes WHERE fact_id = ? AND agent = ?",\n   475\t                
(fact_id, agent),\n   476\t            )\n   477\t        else:\n   478\t       
conn.execute(\n   479\t                "INSERT OR REPLACE INTO consensus_votes 
(fact_id, agent, vote) VALUES (?, ?, ?)",\n   480\t                (fact_id, 
agent, value),\n   481\t            )\n   482\t        score = 
self._recalculate_consensus(fact_id, conn)\n   483\t        conn.commit()\n   
484\t        logger.info("Agent \'%s\' voted %d on fact #%d (New score: 
%.2f)",\n   485\t                     agent, value, fact_id, score)\n   486\t   
return score\n   487\t\n   488\t    def register_agent(self, name: str, 
agent_type: str = "ai", public_key: str = "", tenant_id: str = "default") -> 
str:\n   489\t        """Register a new agent for Reputation-Weighted 
Consensus.\n   490\t\n   491\t        Returns:\n   492\t            The unique 
agent UUID.\n   493\t        """\n   494\t        import uuid\n   495\t        
agent_id = str(uuid.uuid4())\n   496\t        conn = self._get_conn()\n   497\t 
conn.execute(\n   498\t            """\n   499\t            INSERT INTO agents 
(id, name, agent_type, public_key, tenant_id)\n   500\t            VALUES (?, ?,
?, ?, ?)\n   501\t            """,\n   502\t            (agent_id, name, 
agent_type, public_key, tenant_id),\n   503\t        )\n   504\t        
conn.commit()\n   505\t        logger.info("Registered new agent: %s (%s)", 
name, agent_id)\n   506\t        return agent_id\n   507\t\n   508\t    def 
vote_v2(self, fact_id: int, agent_id: str, value: int, reason: Optional[str] = 
None) -> float:\n   509\t        """Cast a reputation-weighted vote (RWC 
v2)."""\n   510\t        conn = self._get_conn()\n   511\t        \n   512\t    
# 1. Fetch agent reputation\n   513\t        agent = conn.execute(\n   514\t    
"SELECT reputation_score FROM agents WHERE id = ? AND is_active = 1",\n   515\t 
(agent_id,)\n   516\t        ).fetchone()\n   517\t        \n   518\t        if 
not agent:\n   519\t            raise ValueError(f"Agent {agent_id} not found or
inactive")\n   520\t        \n   521\t        rep = agent[0]\n   522\t        \n
523\t        if value == 0:\n   524\t            conn.execute(\n   525\t        
"DELETE FROM consensus_votes_v2 WHERE fact_id = ? AND agent_id = ?",\n   526\t  
(fact_id, agent_id)\n   527\t            )\n   528\t        else:\n   529\t     
# 2. Record vote with current reputation snapshot\n   530\t            
conn.execute(\n   531\t                """\n   532\t                INSERT OR 
REPLACE INTO consensus_votes_v2 \n   533\t                (fact_id, agent_id, 
vote, vote_weight, agent_rep_at_vote, vote_reason)\n   534\t                
VALUES (?, ?, ?, ?, ?, ?)\n   535\t                """,\n   536\t               
(fact_id, agent_id, value, rep, rep, reason)\n   537\t            )\n   538\t   
\n   539\t        # 3. Recalculate and commit\n   540\t        score = 
self._recalculate_consensus_v2(fact_id, conn)\n   541\t        conn.commit()\n  
542\t        return score\n   543\t\n   544\t    def 
_recalculate_consensus_v2(self, fact_id: int, conn: sqlite3.Connection) -> 
float:\n   545\t        """Calculate consensus score using reputation 
weights."""\n   546\t        # Query all active votes for this fact\n   547\t   
votes = conn.execute(\n   548\t            """\n   549\t            SELECT 
v.vote, v.vote_weight, a.reputation_score\n   550\t            FROM 
consensus_votes_v2 v\n   551\t            JOIN agents a ON v.agent_id = a.id\n  
552\t            WHERE v.fact_id = ? AND a.is_active = 1\n   553\t            
""",\n   554\t            (fact_id,)\n   555\t        ).fetchall()\n   556\t\n  
557\t        if not votes:\n   558\t            # Fall back to legacy if no v2 
votes exist yet? \n   559\t            # For now, we\'ll return the legacy score
if v2 is empty\n   560\t            return self._recalculate_consensus(fact_id, 
conn)\n   561\t\n   562\t        weighted_sum = 0.0\n   563\t        
total_weight = 0.0\n   564\t        \n   565\t        for vote, vote_weight, 
current_rep in votes:\n   566\t            # Use the higher of recorded weight 
or current reputation\n   567\t            # (or just current rep depending on 
policy)\n   568\t            weight = max(vote_weight, current_rep)\n   569\t   
weighted_sum += vote * weight\n   570\t            total_weight += weight\n   
571\t\n   572\t        if total_weight > 0:\n   573\t            normalized = 
weighted_sum / total_weight  # Range [-1, 1]\n   574\t            score = 1.0 + 
normalized  # Scale to [0, 2]\n   575\t        else:\n   576\t            score 
= 1.0\n   577\t\n   578\t        # Update fact\n   579\t        new_confidence =
None\n   580\t        if score >= 1.6: new_confidence = "verified"\n   581\t    
elif score <= 0.4: new_confidence = "disputed"\n   582\t        \n   583\t      
if new_confidence:\n   584\t            conn.execute(\n   585\t                
"UPDATE facts SET consensus_score = ?, confidence = ? WHERE id = ?",\n   586\t  
(score, new_confidence, fact_id)\n   587\t            )\n   588\t        else:\n
589\t            conn.execute(\n   590\t                "UPDATE facts SET 
consensus_score = ? WHERE id = ?",\n   591\t                (score, fact_id)\n  
592\t            )\n   593\t            \n   594\t        return score\n   
595\t\n   596\t    def _recalculate_consensus(self, fact_id: int, conn: 
sqlite3.Connection) -> float:\n   597\t        """Update consensus_score based 
on votes and adjust confidence."""\n   598\t        row = conn.execute(\n   
599\t            "SELECT SUM(vote) FROM consensus_votes WHERE fact_id = ?",\n   
600\t            (fact_id,),\n   601\t        ).fetchone()\n   602\t        
vote_sum = row[0] or 0\n   603\t        # Score starts at 1.0 (neutral). Each 
vote adds/removes 0.1.\n   604\t        # Verified threshold: 1.5 (net +5 
votes)\n   605\t        # Disputed threshold: 0.5 (net -5 votes)\n   606\t      
score = max(0.0, 1.0 + (vote_sum * 0.1))\n   607\t\n   608\t        # Thresholds
for automatic confidence shifting\n   609\t        new_confidence = None\n   
610\t        if score >= 1.5:\n   611\t            new_confidence = "verified"\n
612\t        elif score <= 0.5:\n   613\t            new_confidence = 
"disputed"\n   614\t\n   615\t        if new_confidence:\n   616\t            
conn.execute(\n   617\t                "UPDATE facts SET consensus_score = ?, 
confidence = ? WHERE id = ?",\n   618\t                (score, new_confidence, 
fact_id),\n   619\t            )\n   620\t        else:\n   621\t            
conn.execute(\n   622\t                "UPDATE facts SET consensus_score = ? 
WHERE id = ?",\n   623\t                (score, fact_id),\n   624\t            
)\n   625\t        return score\n   626\t\n   627\t    # ─── History (Temporal 
Query) ─────────────────────────────────\n   628\t\n   629\t    def history(\n  
630\t        self,\n   631\t        project: str,\n   632\t        as_of: 
Optional[str] = None,\n   633\t    ) -> list[Fact]:\n   634\t        """Get 
facts as they were at a specific point in time.\n   635\t\n   636\t        
Args:\n   637\t            project: Project identifier.\n   638\t            
as_of: ISO 8601 timestamp. None = all facts ever.\n   639\t\n   640\t        
Returns:\n   641\t            List of Facts valid at the given time.\n   642\t  
"""\n   643\t        conn = self._get_conn()\n   644\t\n   645\t        if 
as_of:\n   646\t            clause, params = 
build_temporal_filter_params(as_of)\n   647\t            query = f"""\n   648\t 
SELECT id, project, content, fact_type, tags, confidence,\n   649\t             
valid_from, valid_until, source, meta\n   650\t                FROM facts\n   
651\t                WHERE project = ? AND {clause}\n   652\t                
ORDER BY valid_from DESC\n   653\t                """\n   654\t            # 
Combine params safely\n   655\t            full_params = [project] + params\n   
656\t            cursor = conn.execute(query, full_params)\n   657\t        
else:\n   658\t            cursor = conn.execute(\n   659\t                """\n
660\t                SELECT id, project, content, fact_type, tags, confidence,\n
661\t                       valid_from, valid_until, source, meta\n   662\t     
FROM facts\n   663\t                WHERE project = ?\n   664\t                
ORDER BY valid_from DESC\n   665\t                """,\n   666\t                
(project,),\n   667\t            )\n   668\t\n   669\t        return 
[self._row_to_fact(row) for row in cursor.fetchall()]\n   670\t\n   671\t    # 
─── Deprecate ────────────────────────────────────────────────\n   672\t\n   
673\t    def deprecate(self, fact_id: int, reason: Optional[str] = None) -> 
bool:\n   674\t        """Mark a fact as no longer valid. Never deletes.\n   
675\t\n   676\t        Args:\n   677\t            fact_id: The fact to 
deprecate.\n   678\t            reason: Optional reason for deprecation.\n   
679\t\n   680\t        Returns:\n   681\t            True if fact was found and 
deprecated.\n   682\t        """\n   683\t        if fact_id <= 0:\n   684\t    
raise ValueError("Invalid fact_id")\n   685\t\n   686\t        conn = 
self._get_conn()\n   687\t        ts = now_iso()\n   688\t\n   689\t        
result = conn.execute(\n   690\t            """\n   691\t            UPDATE 
facts\n   692\t            SET valid_until = ?, updated_at = ?,\n   693\t       
meta = json_set(COALESCE(meta, \'{}\'), \'$.deprecation_reason\', ?)\n   694\t  
WHERE id = ? AND valid_until IS NULL\n   695\t            """,\n   696\t        
(ts, ts, reason or "deprecated", fact_id),\n   697\t        )\n   698\t\n   
699\t        if result.rowcount > 0:\n   700\t            # Fetch project for 
transaction log\n   701\t            row = conn.execute("SELECT project FROM 
facts WHERE id = ?", (fact_id,)).fetchone()\n   702\t            project = 
row[0] if row else "__unknown__"\n   703\t\n   704\t            
self._log_transaction(conn, project, "deprecate", {\n   705\t                
"fact_id": fact_id,\n   706\t                "reason": reason,\n   707\t        
})\n   708\t            conn.commit()\n   709\t            
logger.info("Deprecated fact #%d", fact_id)\n   710\t            return True\n  
711\t\n   712\t        return False\n   713\t\n   714\t    # ─── Stats 
────────────────────────────────────────────────────\n   715\t\n   716\t    def 
stats(self) -> dict:\n   717\t        """Get database statistics."""\n   718\t  
conn = self._get_conn()\n   719\t\n   720\t        total = conn.execute("SELECT 
COUNT(*) FROM facts").fetchone()[0]\n   721\t        active = conn.execute(\n   
722\t            "SELECT COUNT(*) FROM facts WHERE valid_until IS NULL"\n   
723\t        ).fetchone()[0]\n   724\t        deprecated = total - active\n   
725\t\n   726\t        projects = conn.execute(\n   727\t            "SELECT 
DISTINCT project FROM facts WHERE valid_until IS NULL"\n   728\t        
).fetchall()\n   729\t        project_list = [p[0] for p in projects]\n   
730\t\n   731\t        types = conn.execute(\n   732\t            """\n   733\t 
SELECT fact_type, COUNT(*) FROM facts\n   734\t            WHERE valid_until IS 
NULL\n   735\t            GROUP BY fact_type\n   736\t            """\n   737\t 
).fetchall()\n   738\t\n   739\t        if self._vec_available:\n   740\t       
embeddings = conn.execute(\n   741\t                "SELECT COUNT(*) FROM 
fact_embeddings"\n   742\t            ).fetchone()[0]\n   743\t        else:\n  
744\t            embeddings = 0\n   745\t\n   746\t        transactions = 
conn.execute(\n   747\t            "SELECT COUNT(*) FROM transactions"\n   748\t
).fetchone()[0]\n   749\t\n   750\t        return {\n   751\t            
"total_facts": total,\n   752\t            "active_facts": active,\n   753\t    
"deprecated_facts": deprecated,\n   754\t            "projects": project_list,\n
755\t            "project_count": len(project_list),\n   756\t            
"types": {t: c for t, c in types},\n   757\t            "embeddings": 
embeddings,\n   758\t            "transactions": transactions,\n   759\t        
"db_path": str(self._db_path),\n   760\t            "db_size_mb": 
round(self._db_path.stat().st_size / 1_048_576, 2)\n   761\t            if 
self._db_path.exists() else 0,\n   762\t        }\n   763\t\n   764\t    # ─── 
Transaction Ledger ───────────────────────────────────────\n   765\t\n   766\t  
def _log_transaction(\n   767\t        self,\n   768\t        conn: 
sqlite3.Connection,\n   769\t        project: str,\n   770\t        action: 
str,\n   771\t        detail: dict,\n   772\t    ) -> None:\n   773\t        
"""Log an action to the immutable transaction ledger."""\n   774\t        
detail_json = json.dumps(detail, default=str)\n   775\t        ts = now_iso()\n 
776\t\n   777\t        # Get previous hash for chain\n   778\t        prev = 
conn.execute(\n   779\t            "SELECT hash FROM transactions ORDER BY id 
DESC LIMIT 1"\n   780\t        ).fetchone()\n   781\t        prev_hash = prev[0]
if prev else "GENESIS"\n   782\t\n   783\t        # Compute hash: 
SHA-256(prev_hash + project + action + detail + timestamp)\n   784\t        
hash_input = f"{prev_hash}:{project}:{action}:{detail_json}:{ts}"\n   785\t     
tx_hash = hashlib.sha256(hash_input.encode()).hexdigest()\n   786\t\n   787\t   
conn.execute(\n   788\t            """\n   789\t            INSERT INTO 
transactions (project, action, detail, prev_hash, hash, timestamp)\n   790\t    
VALUES (?, ?, ?, ?, ?, ?)\n   791\t            """,\n   792\t            
(project, action, detail_json, prev_hash, tx_hash, ts),\n   793\t        )\n   
794\t\n   795\t    # ─── Helpers 
──────────────────────────────────────────────────\n   796\t\n   797\t    
@staticmethod\n   798\t    def _row_to_fact(row: tuple) -> Fact:\n   799\t      
"""Convert a database row to a Fact object."""\n   800\t        try:\n   801\t  
tags = json.loads(row[4]) if row[4] else []\n   802\t        except 
(json.JSONDecodeError, TypeError):\n   803\t            tags = []\n   804\t     
\n   805\t        try:\n   806\t            meta = json.loads(row[9]) if row[9] 
else {}\n   807\t        except (json.JSONDecodeError, TypeError):\n   808\t    
meta = {}\n   809\t\n   810\t        return Fact(\n   811\t            
id=row[0],\n   812\t            project=row[1],\n   813\t            
content=row[2],\n   814\t            fact_type=row[3],\n   815\t            
tags=tags,\n   816\t            confidence=row[5],\n   817\t            
valid_from=row[6],\n   818\t            valid_until=row[7],\n   819\t           
source=row[8],\n   820\t            meta=meta,\n   821\t            
consensus_score=row[10] if len(row) > 10 else 1.0,\n   822\t        )\n   
823\t\n   824\t    def close(self) -> None:\n   825\t        """Close database 
connection."""\n   826\t        if self._conn:\n   827\t            
self._conn.close()\n   828\t            self._conn = None\n   829\t\n   830\t   
def __enter__(self):\n   831\t        return self\n   832\t\n   833\t    def 
__exit__(self, *args):\n   834\t        self.close()\n   835\t\n   836\t    def 
__repr__(self) -> str:\n   837\t        return 
f"CortexEngine(db=\'{self._db_path}\')"\n',
        message='837 lines read from file starting from line 1. End of file 
reached.',
        display=[],
        extras=None
    )
)
ToolCallPart(arguments_part='orjafernandezangulo/cortex/cortex/schema.py"}')
ToolCall(
    type='function',
    id='tool_HYXS7G5tWwbHklykxkRpNfV4',
    function=FunctionBody(name='ReadFile', arguments='{"path": "/Users'),
    extras=None
)
ToolResult(
    tool_call_id='tool_wPLABfBAoxlTT38ZdDj48ymR',
    return_value=ToolOk(
        is_error=False,
        output='     1\t"""\n     2\tCORTEX v4.0 — SQLite Schema Definitions.\n 
3\t\n     4\tAll tables, indexes, and virtual tables for the sovereign memory 
engine.\n     5\t"""\n     6\t\n     7\tSCHEMA_VERSION = "4.0.0"\n     8\t\n    
9\t# ─── Core Facts Table ────────────────────────────────────────────────\n    
10\tCREATE_FACTS = """\n    11\tCREATE TABLE IF NOT EXISTS facts (\n    12\t    
id          INTEGER PRIMARY KEY AUTOINCREMENT,\n    13\t    project     TEXT NOT
NULL,\n    14\t    content     TEXT NOT NULL,\n    15\t    fact_type   TEXT NOT 
NULL DEFAULT \'knowledge\',\n    16\t    tags        TEXT NOT NULL DEFAULT 
\'[]\',\n    17\t    confidence  TEXT NOT NULL DEFAULT \'stated\',\n    18\t    
valid_from  TEXT NOT NULL,\n    19\t    valid_until TEXT,\n    20\t    source   
TEXT,\n    21\t    meta        TEXT DEFAULT \'{}\',\n    22\t    consensus_score
REAL DEFAULT 1.0,\n    23\t    created_at  TEXT NOT NULL DEFAULT 
(datetime(\'now\')),\n    24\t    updated_at  TEXT NOT NULL DEFAULT 
(datetime(\'now\'))\n    25\t);\n    26\t"""\n    27\t\n    
28\tCREATE_FACTS_INDEXES = """\n    29\tCREATE INDEX IF NOT EXISTS 
idx_facts_project ON facts(project);\n    30\tCREATE INDEX IF NOT EXISTS 
idx_facts_type ON facts(fact_type);\n    31\tCREATE INDEX IF NOT EXISTS 
idx_facts_proj_type ON facts(project, fact_type);\n    32\tCREATE INDEX IF NOT 
EXISTS idx_facts_valid ON facts(valid_from, valid_until);\n    33\tCREATE INDEX 
IF NOT EXISTS idx_facts_confidence ON facts(confidence);\n    34\t"""\n    
35\t\n    36\t# ─── Vector Embeddings (sqlite-vec) 
──────────────────────────────────\n    37\tCREATE_EMBEDDINGS = """\n    
38\tCREATE VIRTUAL TABLE IF NOT EXISTS fact_embeddings USING vec0(\n    39\t    
fact_id INTEGER PRIMARY KEY,\n    40\t    embedding FLOAT[384]\n    41\t);\n    
42\t"""\n    43\t\n    44\t# ─── Sessions Log 
────────────────────────────────────────────────────\n    45\tCREATE_SESSIONS = 
"""\n    46\tCREATE TABLE IF NOT EXISTS sessions (\n    47\t    id              
TEXT PRIMARY KEY,\n    48\t    date            TEXT NOT NULL,\n    49\t    focus
TEXT NOT NULL DEFAULT \'[]\',\n    50\t    summary         TEXT NOT NULL,\n    
51\t    conversations   INTEGER NOT NULL DEFAULT 1,\n    52\t    created_at     
TEXT NOT NULL DEFAULT (datetime(\'now\'))\n    53\t);\n    54\t"""\n    55\t\n  
56\t# ─── Transaction Ledger (append-only, hash-chained) ──────────────────\n   
57\tCREATE_TRANSACTIONS = """\n    58\tCREATE TABLE IF NOT EXISTS transactions 
(\n    59\t    id          INTEGER PRIMARY KEY AUTOINCREMENT,\n    60\t    
project     TEXT NOT NULL,\n    61\t    action      TEXT NOT NULL,\n    62\t    
detail      TEXT,\n    63\t    prev_hash   TEXT,\n    64\t    hash        TEXT 
NOT NULL,\n    65\t    timestamp   TEXT NOT NULL DEFAULT (datetime(\'now\'))\n  
66\t);\n    67\t"""\n    68\t\n    69\tCREATE_TRANSACTIONS_INDEX = """\n    
70\tCREATE INDEX IF NOT EXISTS idx_tx_project ON transactions(project);\n    
71\tCREATE INDEX IF NOT EXISTS idx_tx_action ON transactions(action);\n    
72\t"""\n    73\t\n    74\t# ─── Heartbeats (activity pulses for time tracking) 
──────────────────\n    75\tCREATE_HEARTBEATS = """\n    76\tCREATE TABLE IF NOT
EXISTS heartbeats (\n    77\t    id          INTEGER PRIMARY KEY 
AUTOINCREMENT,\n    78\t    project     TEXT NOT NULL,\n    79\t    entity      
TEXT,\n    80\t    category    TEXT NOT NULL,\n    81\t    branch      TEXT,\n  
82\t    language    TEXT,\n    83\t    timestamp   TEXT NOT NULL,\n    84\t    
meta        TEXT DEFAULT \'{}\'\n    85\t);\n    86\t"""\n    87\t\n    
88\tCREATE_HEARTBEATS_INDEX = """\n    89\tCREATE INDEX IF NOT EXISTS 
idx_hb_project ON heartbeats(project);\n    90\tCREATE INDEX IF NOT EXISTS 
idx_hb_timestamp ON heartbeats(timestamp);\n    91\tCREATE INDEX IF NOT EXISTS 
idx_hb_category ON heartbeats(category);\n    92\t"""\n    93\t\n    94\t# ─── 
Time Entries (grouped heartbeat blocks) ─────────────────────────\n    
95\tCREATE_TIME_ENTRIES = """\n    96\tCREATE TABLE IF NOT EXISTS time_entries 
(\n    97\t    id          INTEGER PRIMARY KEY AUTOINCREMENT,\n    98\t    
project     TEXT NOT NULL,\n    99\t    category    TEXT NOT NULL,\n   100\t    
start_time  TEXT NOT NULL,\n   101\t    end_time    TEXT NOT NULL,\n   102\t    
duration_s  INTEGER NOT NULL,\n   103\t    entities    TEXT DEFAULT \'[]\',\n   
104\t    heartbeats  INTEGER DEFAULT 0,\n   105\t    meta        TEXT DEFAULT 
\'{}\'\n   106\t);\n   107\t"""\n   108\t\n   109\tCREATE_TIME_ENTRIES_INDEX = 
"""\n   110\tCREATE INDEX IF NOT EXISTS idx_te_project ON 
time_entries(project);\n   111\tCREATE INDEX IF NOT EXISTS idx_te_start ON 
time_entries(start_time);\n   112\t"""\n   113\t\n   114\t# ─── Metadata Table 
──────────────────────────────────────────────────\n   115\tCREATE_META = """\n 
116\tCREATE TABLE IF NOT EXISTS cortex_meta (\n   117\t    key     TEXT PRIMARY 
KEY,\n   118\t    value   TEXT NOT NULL\n   119\t);\n   120\t"""\n   121\t\n   
122\t# ─── Consensus Votes (Neural Swarm Consensus) ───────────────────────\n   
123\tCREATE_VOTES = """\n   124\tCREATE TABLE IF NOT EXISTS consensus_votes (\n 
125\t    id      INTEGER PRIMARY KEY AUTOINCREMENT,\n   126\t    fact_id INTEGER
NOT NULL REFERENCES facts(id),\n   127\t    agent   TEXT NOT NULL,\n   128\t    
vote    INTEGER NOT NULL, -- 1 (verify), -1 (dispute)\n   129\t    timestamp 
TEXT NOT NULL DEFAULT (datetime(\'now\')),\n   130\t    UNIQUE(fact_id, agent)\n
131\t);\n   132\t"""\n   133\t\n   134\t# ─── Reputation-Weighted Consensus (v2)
─────────────────────────────\n   135\tCREATE_AGENTS = """\n   136\tCREATE TABLE
IF NOT EXISTS agents (\n   137\t    id              TEXT PRIMARY KEY,\n   138\t 
public_key      TEXT NOT NULL,\n   139\t    name            TEXT NOT NULL,\n   
140\t    agent_type      TEXT NOT NULL DEFAULT \'ai\',\n   141\t    tenant_id   
TEXT NOT NULL DEFAULT \'default\',\n   142\t    created_at      TEXT NOT NULL 
DEFAULT (datetime(\'now\')),\n   143\t    reputation_score    REAL NOT NULL 
DEFAULT 0.5,\n   144\t    reputation_stake    REAL NOT NULL DEFAULT 0.0,\n   
145\t    total_votes         INTEGER DEFAULT 0,\n   146\t    successful_votes   
INTEGER DEFAULT 0,\n   147\t    disputed_votes      INTEGER DEFAULT 0,\n   148\t
last_active_at      TEXT NOT NULL DEFAULT (datetime(\'now\')),\n   149\t    
is_active           BOOLEAN DEFAULT TRUE,\n   150\t    is_verified         
BOOLEAN DEFAULT FALSE,\n   151\t    meta                TEXT DEFAULT \'{}\'\n   
152\t);\n   153\t"""\n   154\t\n   155\tCREATE_VOTES_V2 = """\n   156\tCREATE 
TABLE IF NOT EXISTS consensus_votes_v2 (\n   157\t    id              INTEGER 
PRIMARY KEY AUTOINCREMENT,\n   158\t    fact_id         INTEGER NOT NULL 
REFERENCES facts(id),\n   159\t    agent_id        TEXT NOT NULL REFERENCES 
agents(id),\n   160\t    vote            INTEGER NOT NULL,\n   161\t    
vote_weight     REAL NOT NULL,\n   162\t    agent_rep_at_vote   REAL NOT NULL,\n
163\t    stake_at_vote       REAL DEFAULT 0.0,\n   164\t    created_at      TEXT
NOT NULL DEFAULT (datetime(\'now\')),\n   165\t    decay_factor    REAL DEFAULT 
1.0,\n   166\t    vote_reason     TEXT,\n   167\t    meta            TEXT 
DEFAULT \'{}\',\n   168\t    UNIQUE(fact_id, agent_id)\n   169\t);\n   
170\t"""\n   171\t\n   172\tCREATE_TRUST_EDGES = """\n   173\tCREATE TABLE IF 
NOT EXISTS trust_edges (\n   174\t    id              INTEGER PRIMARY KEY 
AUTOINCREMENT,\n   175\t    source_agent    TEXT NOT NULL REFERENCES 
agents(id),\n   176\t    target_agent    TEXT NOT NULL REFERENCES agents(id),\n 
177\t    trust_weight    REAL NOT NULL,\n   178\t    created_at      TEXT NOT 
NULL DEFAULT (datetime(\'now\')),\n   179\t    updated_at      TEXT NOT NULL 
DEFAULT (datetime(\'now\')),\n   180\t    UNIQUE(source_agent, target_agent)\n  
181\t);\n   182\t"""\n   183\t\n   184\tCREATE_OUTCOMES = """\n   185\tCREATE 
TABLE IF NOT EXISTS consensus_outcomes (\n   186\t    id              INTEGER 
PRIMARY KEY AUTOINCREMENT,\n   187\t    fact_id         INTEGER NOT NULL 
REFERENCES facts(id),\n   188\t    final_state     TEXT NOT NULL,\n   189\t    
final_score     REAL NOT NULL,\n   190\t    resolved_at     TEXT NOT NULL 
DEFAULT (datetime(\'now\')),\n   191\t    total_votes     INTEGER NOT NULL,\n   
192\t    unique_agents   INTEGER NOT NULL,\n   193\t    reputation_sum  REAL NOT
NULL,\n   194\t    resolution_method   TEXT DEFAULT \'reputation_weighted\',\n  
195\t    meta                TEXT DEFAULT \'{}\'\n   196\t);\n   197\t"""\n   
198\t\n   199\tCREATE_RWC_INDEXES = """\n   200\tCREATE INDEX IF NOT EXISTS 
idx_agents_reputation ON agents(reputation_score DESC);\n   201\tCREATE INDEX IF
NOT EXISTS idx_agents_active ON agents(is_active, last_active_at);\n   
202\tCREATE INDEX IF NOT EXISTS idx_votes_v2_fact ON 
consensus_votes_v2(fact_id);\n   203\tCREATE INDEX IF NOT EXISTS 
idx_votes_v2_agent ON consensus_votes_v2(agent_id);\n   204\tCREATE INDEX IF NOT
EXISTS idx_trust_source ON trust_edges(source_agent);\n   205\tCREATE INDEX IF 
NOT EXISTS idx_trust_target ON trust_edges(target_agent);\n   206\t"""\n   
207\t\n   208\t# ─── All statements in order 
─────────────────────────────────────────\n   209\tALL_SCHEMA = [\n   210\t    
CREATE_FACTS,\n   211\t    CREATE_FACTS_INDEXES,\n   212\t    
CREATE_EMBEDDINGS,\n   213\t    CREATE_SESSIONS,\n   214\t    
CREATE_TRANSACTIONS,\n   215\t    CREATE_TRANSACTIONS_INDEX,\n   216\t    
CREATE_HEARTBEATS,\n   217\t    CREATE_HEARTBEATS_INDEX,\n   218\t    
CREATE_TIME_ENTRIES,\n   219\t    CREATE_TIME_ENTRIES_INDEX,\n   220\t    
CREATE_META,\n   221\t    CREATE_VOTES,\n   222\t    CREATE_AGENTS,\n   223\t   
CREATE_VOTES_V2,\n   224\t    CREATE_TRUST_EDGES,\n   225\t    
CREATE_OUTCOMES,\n   226\t    CREATE_RWC_INDEXES,\n   227\t]\n   228\t\n   
229\t\n   230\tdef get_init_meta() -> list[tuple[str, str]]:\n   231\t    
"""Return initial metadata key-value pairs."""\n   232\t    return [\n   233\t  
("schema_version", SCHEMA_VERSION),\n   234\t        ("engine", "cortex"),\n   
235\t        ("created_by", "cortex-init"),\n   236\t    ]\n',
        message='236 lines read from file starting from line 1. End of file 
reached.',
        display=[],
        extras=None
    )
)
ToolCallPart(
    arguments_part='/borjafernandezangulo/cortex/cortex/mcp_server.py"}'
)
StatusUpdate(
    context_usage=0.10919952392578125,
    token_usage=TokenUsage(
        input_other=22226,
        output=148,
        input_cache_read=6400,
        input_cache_creation=0
    ),
    message_id='chatcmpl-NJiKF34KJUK1Ppx4zIP3OPqI'
)
ToolResult(
    tool_call_id='tool_HYXS7G5tWwbHklykxkRpNfV4',
    return_value=ToolOk(
        is_error=False,
        output='     1\t"""\n     2\tCORTEX v4.0 — MCP Server.\n     3\t\n     
4\tModel Context Protocol server exposing CORTEX as tools for any AI agent.\n   
5\tUses FastMCP (mcp Python SDK) for stdio transport.\n     6\t"""\n     7\t\n  
8\tfrom __future__ import annotations\n     9\t\n    10\timport atexit\n    
11\timport json\n    12\timport logging\n    13\tfrom typing import Optional\n  
14\t\n    15\tlogger = logging.getLogger("cortex.mcp")\n    16\t\n    
17\t__all__ = ["create_mcp_server", "run_server"]\n    18\t\n    19\t# ─── 
Server Setup ─────────────────────────────────────────────────────\n    20\t\n  
21\t_MCP_AVAILABLE = False\n    22\ttry:\n    23\t    from mcp.server.fastmcp 
import FastMCP\n    24\t    _MCP_AVAILABLE = True\n    25\texcept ImportError:\n
26\t    FastMCP = None  # type: ignore\n    27\t    logger.debug("MCP SDK not 
installed. Install with: pip install \'cortex-memory[mcp]\'")\n    28\t\n    
29\t\n    30\tdef create_mcp_server(db_path: str = "~/.cortex/cortex.db") -> 
"FastMCP":\n    31\t    """Create and configure a CORTEX MCP server instance.\n 
32\t\n    33\t    Args:\n    34\t        db_path: Path to CORTEX database.\n    
35\t\n    36\t    Returns:\n    37\t        Configured FastMCP server ready to 
run.\n    38\t\n    39\t    Raises:\n    40\t        ImportError: If MCP SDK is 
not installed.\n    41\t    """\n    42\t    if not _MCP_AVAILABLE:\n    43\t   
raise ImportError(\n    44\t            "MCP SDK not installed. Install with: 
pip install mcp\\n"\n    45\t            "Or: pip install 
\'cortex-memory[mcp]\'"\n    46\t        )\n    47\t\n    48\t    from 
cortex.engine import CortexEngine\n    49\t\n    50\t    mcp = FastMCP(\n    
51\t        "CORTEX Memory",\n    52\t        description="Sovereign memory 
infrastructure for AI agents. "\n    53\t        "Store, search, and recall 
facts with semantic search and temporal queries.",\n    54\t    )\n    55\t\n   
56\t    # Lazy engine initialization\n    57\t    _engine: dict = {}\n    58\t\n
59\t    def get_engine() -> CortexEngine:\n    60\t        if "instance" not in 
_engine:\n    61\t            eng = CortexEngine(db_path=db_path)\n    62\t     
eng.init_db()\n    63\t            _engine["instance"] = eng\n    64\t          
atexit.register(eng.close)\n    65\t        return _engine["instance"]\n    
66\t\n    67\t    # ─── Tools 
────────────────────────────────────────────────────\n    68\t\n    69\t    
@mcp.tool()\n    70\t    def cortex_store(\n    71\t        project: str,\n    
72\t        content: str,\n    73\t        fact_type: str = "knowledge",\n    
74\t        tags: str = "[]",\n    75\t        source: str = "",\n    76\t    ) 
-> str:\n    77\t        """Store a fact in CORTEX memory.\n    78\t\n    79\t  
Args:\n    80\t            project: Project/namespace for the fact (e.g., 
\'myproject\').\n    81\t            content: The fact content to store.\n    
82\t            fact_type: Type: knowledge, decision, mistake, bridge, ghost.\n 
83\t            tags: JSON array of tags, e.g. \'["important", "bug"]\'.\n    
84\t            source: Where this fact came from.\n    85\t\n    86\t        
Returns:\n    87\t            Confirmation with the fact ID.\n    88\t        
"""\n    89\t        engine = get_engine()\n    90\t        try:\n    91\t      
parsed_tags = json.loads(tags) if tags else []\n    92\t        except 
json.JSONDecodeError:\n    93\t            parsed_tags = []\n    94\t\n    95\t 
fact_id = engine.store(\n    96\t            project=project,\n    97\t         
content=content,\n    98\t            fact_type=fact_type,\n    99\t            
tags=parsed_tags,\n   100\t            source=source or None,\n   101\t        
)\n   102\t        return f"✓ Stored fact #{fact_id} in project \'{project}\'"\n
103\t\n   104\t    @mcp.tool()\n   105\t    def cortex_search(\n   106\t        
query: str,\n   107\t        project: str = "",\n   108\t        top_k: int = 
5,\n   109\t    ) -> str:\n   110\t        """Search CORTEX memory using 
semantic + text hybrid search.\n   111\t\n   112\t        Args:\n   113\t       
query: Natural language search query.\n   114\t            project: Optional 
project filter.\n   115\t            top_k: Number of results (1-20).\n   
116\t\n   117\t        Returns:\n   118\t            Formatted search results 
with scores.\n   119\t        """\n   120\t        engine = get_engine()\n   
121\t        results = engine.search(\n   122\t            query=query,\n   
123\t            project=project or None,\n   124\t            
top_k=min(max(top_k, 1), 20),\n   125\t        )\n   126\t\n   127\t        if 
not results:\n   128\t            return "No results found."\n   129\t\n   130\t
lines = [f"Found {len(results)} results:\\n"]\n   131\t        for r in 
results:\n   132\t            lines.append(\n   133\t                
f"[#{r.fact_id}] (score: {r.score:.3f}) "\n   134\t                
f"[{r.project}/{r.fact_type}]\\n{r.content}\\n"\n   135\t            )\n   136\t
return "\\n".join(lines)\n   137\t\n   138\t    @mcp.tool()\n   139\t    def 
cortex_recall(\n   140\t        project: str,\n   141\t        limit: int = 
20,\n   142\t    ) -> str:\n   143\t        """Load all active facts for a 
project.\n   144\t\n   145\t        Args:\n   146\t            project: Project 
to recall facts from.\n   147\t            limit: Maximum facts to return.\n   
148\t\n   149\t        Returns:\n   150\t            Formatted list of project 
facts.\n   151\t        """\n   152\t        engine = get_engine()\n   153\t    
facts = engine.recall(project=project, limit=limit)\n   154\t\n   155\t        
if not facts:\n   156\t            return f"No facts found for project 
\'{project}\'."\n   157\t\n   158\t        lines = [f"📁 {project} — 
{len(facts)} facts:\\n"]\n   159\t        for f in facts:\n   160\t            
try:\n   161\t                tags = f.tags if isinstance(f.tags, list) else 
json.loads(f.tags) if isinstance(f.tags, str) else []\n   162\t            
except (json.JSONDecodeError, TypeError):\n   163\t                tags = []\n  
164\t            tag_str = f" [{\', \'.join(tags)}]" if tags else ""\n   165\t  
lines.append(f"  #{f.id} [{f.fact_type}]{tag_str}: {f.content[:200]}")\n   166\t
return "\\n".join(lines)\n   167\t\n   168\t    @mcp.tool()\n   169\t    def 
cortex_graph(\n   170\t        project: str = "",\n   171\t        limit: int = 
30,\n   172\t    ) -> str:\n   173\t        """Show the entity-relationship 
knowledge graph.\n   174\t\n   175\t        Args:\n   176\t            project: 
Optional project filter.\n   177\t            limit: Max entities to show.\n   
178\t\n   179\t        Returns:\n   180\t            Formatted entity graph with
relationships.\n   181\t        """\n   182\t        engine = get_engine()\n   
183\t        data = engine.graph(project=project or None, limit=limit)\n   
184\t\n   185\t        if not data["entities"]:\n   186\t            return "No 
entities in the knowledge graph yet."\n   187\t\n   188\t        lines = [f"🧠 
Knowledge Graph ({data[\'stats\'][\'total_entities\']} entities, "\n   189\t    
f"{data[\'stats\'][\'total_relationships\']} relationships):\\n"]\n   190\t\n   
191\t        for ent in data["entities"]:\n   192\t            lines.append(f"  
• {ent[\'name\']} ({ent[\'type\']}) — {ent[\'mentions\']} mentions")\n   193\t\n
194\t        if data["relationships"]:\n   195\t            
lines.append("\\nRelationships:")\n   196\t            id_to_name = {e["id"]: 
e["name"] for e in data["entities"]}\n   197\t            for rel in 
sorted(data["relationships"], key=lambda r: -r["weight"])[:10]:\n   198\t       
src = id_to_name.get(rel["source"], f"#{rel[\'source\']}")\n   199\t            
tgt = id_to_name.get(rel["target"], f"#{rel[\'target\']}")\n   200\t            
lines.append(f"  {src} ──[{rel[\'type\']}]── {tgt} (w={rel[\'weight\']:.1f})")\n
201\t\n   202\t        return "\\n".join(lines)\n   203\t\n   204\t    
@mcp.tool()\n   205\t    def cortex_status() -> str:\n   206\t        """Get 
CORTEX system status and statistics.\n   207\t\n   208\t        Returns:\n   
209\t            System health and statistics summary.\n   210\t        """\n   
211\t        engine = get_engine()\n   212\t        stats = engine.stats()\n   
213\t        return (\n   214\t            f"CORTEX Status:\\n"\n   215\t       
f"  Facts: {stats.get(\'total_facts\', 0)} total, "\n   216\t            
f"{stats.get(\'active_facts\', 0)} active\\n"\n   217\t            f"  Projects:
{stats.get(\'projects\', 0)}\\n"\n   218\t            f"  Embeddings: 
{stats.get(\'embeddings\', 0)}\\n"\n   219\t            f"  DB Size: 
{stats.get(\'db_size_mb\', 0):.1f} MB"\n   220\t        )\n   221\t\n   222\t   
# ─── Resources ────────────────────────────────────────────────\n   223\t\n   
224\t    @mcp.resource("cortex://projects")\n   225\t    def list_projects() -> 
str:\n   226\t        """List all projects in CORTEX memory."""\n   227\t       
engine = get_engine()\n   228\t        conn = engine.get_connection()\n   229\t 
rows = conn.execute(\n   230\t            "SELECT DISTINCT project FROM facts 
WHERE valid_until IS NULL "\n   231\t            "ORDER BY project"\n   232\t   
).fetchall()\n   233\t        projects = [r[0] for r in rows]\n   234\t        
return json.dumps({"projects": projects, "count": len(projects)})\n   235\t\n   
236\t    @mcp.resource("cortex://stats")\n   237\t    def memory_stats() -> 
str:\n   238\t        """Get CORTEX memory statistics."""\n   239\t        
engine = get_engine()\n   240\t        stats = engine.stats()\n   241\t        
return json.dumps(stats)\n   242\t\n   243\t    return mcp\n   244\t\n   245\t\n
246\tdef run_server(db_path: str = "~/.cortex/cortex.db") -> None:\n   247\t    
"""Start the CORTEX MCP server (stdio transport)."""\n   248\t    mcp = 
create_mcp_server(db_path)\n   249\t    logger.info("Starting CORTEX MCP server 
(stdio transport)...")\n   250\t    mcp.run()\n',
        message='250 lines read from file starting from line 1. End of file 
reached.',
        display=[],
        extras=None
    )
)
StepBegin(n=3)
TextPart(
    type='text',
    text='Now let me examine the migrations file and additional key files to 
understand the current state:'
)
ToolCall(
    type='function',
    id='tool_aKA2kYaKXPhcgO6JO8a7C6wU',
    function=FunctionBody(
        name='ReadFile',
        arguments='{"path": 
"/Users/borjafernandezangulo/cortex/cortex/migrations.py"}'
    ),
    extras=None
)
ToolCall(
    type='function',
    id='tool_9MNCXl4YSIhSqfmGldbPfzvW',
    function=FunctionBody(
        name='ReadFile',
        arguments='{"path": "/Users/borjafer'
    ),
    extras=None
)
ToolResult(
    tool_call_id='tool_aKA2kYaKXPhcgO6JO8a7C6wU',
    return_value=ToolOk(
        is_error=False,
        output='     1\t"""\n     2\tCORTEX v4.0 — Schema Migrations.\n     
3\t\n     4\tSimple, forward-only migration system using a version table.\n     
5\tEach migration is a function that receives a connection and applies 
changes.\n     6\t"""\n     7\t\n     8\tfrom __future__ import annotations\n   
9\t\n    10\timport logging\n    11\timport sqlite3\n    12\t\n    13\tlogger = 
logging.getLogger("cortex")\n    14\t\n    15\t\n    16\tdef 
ensure_migration_table(conn: sqlite3.Connection):\n    17\t    """Create the 
schema_version table if it doesn\'t exist."""\n    18\t    conn.execute("""\n   
19\t        CREATE TABLE IF NOT EXISTS schema_version (\n    20\t            
version INTEGER PRIMARY KEY,\n    21\t            applied_at TEXT DEFAULT 
(datetime(\'now\')),\n    22\t            description TEXT\n    23\t        )\n 
24\t    """)\n    25\t    conn.commit()\n    26\t\n    27\t\n    28\tdef 
get_current_version(conn: sqlite3.Connection) -> int:\n    29\t    """Get the 
current schema version (0 means fresh DB)."""\n    30\t    try:\n    31\t       
row = conn.execute(\n    32\t            "SELECT MAX(version) FROM 
schema_version"\n    33\t        ).fetchone()\n    34\t        return row[0] if 
row[0] is not None else 0\n    35\t    except Exception:\n    36\t        return
0\n    37\t\n    38\t\n    39\t# ─── Migration Definitions 
──────────────────────────────────────────\n    40\t\n    41\t\n    42\tdef 
_migration_001_add_updated_at(conn: sqlite3.Connection):\n    43\t    """Add 
updated_at column to facts table if missing."""\n    44\t    columns = {\n    
45\t        row[1] for row in conn.execute("PRAGMA 
table_info(facts)").fetchall()\n    46\t    }\n    47\t    if "updated_at" not 
in columns:\n    48\t        conn.execute("ALTER TABLE facts ADD COLUMN 
updated_at TEXT")\n    49\t        logger.info("Migration 001: Added 
\'updated_at\' column to facts")\n    50\t\n    51\t\n    52\tdef 
_migration_002_add_indexes(conn: sqlite3.Connection):\n    53\t    """Add 
performance indexes."""\n    54\t    conn.execute(\n    55\t        "CREATE 
INDEX IF NOT EXISTS idx_facts_project_active "\n    56\t        "ON 
facts(project, valid_until)"\n    57\t    )\n    58\t    conn.execute(\n    59\t
"CREATE INDEX IF NOT EXISTS idx_facts_type "\n    60\t        "ON 
facts(fact_type)"\n    61\t    )\n    62\t    conn.execute(\n    63\t        
"CREATE INDEX IF NOT EXISTS idx_facts_created "\n    64\t        "ON 
facts(created_at DESC)"\n    65\t    )\n    66\t    logger.info("Migration 002: 
Added performance indexes")\n    67\t\n    68\t\n    69\tdef 
_migration_003_enable_wal(conn: sqlite3.Connection):\n    70\t    """Enable WAL 
mode for better concurrent read performance."""\n    71\t    
conn.execute("PRAGMA journal_mode=WAL")\n    72\t    logger.info("Migration 003:
Enabled WAL journal mode")\n    73\t\n    74\t\n    75\tdef 
_migration_004_vector_index(conn: sqlite3.Connection):\n    76\t    """Add IVF 
index to fact_embeddings for sub-millisecond search."""\n    77\t    # Note: 
sqlite-vec uses a specific syntax for virtual table indexes.\n    78\t    # In 
vec0, we can create an index on the embedding column.\n    79\t    try:\n    
80\t        conn.execute(\n    81\t            "CREATE INDEX IF NOT EXISTS 
idx_fact_embeddings_ivf "\n    82\t            "ON fact_embeddings(embedding) 
USING ivf0"\n    83\t        )\n    84\t        logger.info("Migration 004: 
Added IVF index to fact_embeddings")\n    85\t    except 
sqlite3.OperationalError as e:\n    86\t        # Fallback: if ivf0 is not 
available in the current sqlite-vec build, \n    87\t        # we log it but 
don\'t fail, as brute force KNN still works.\n    88\t        
logger.warning("Migration 004 skipped: IVF index not supported by this build 
(%s)", e)\n    89\t\n    90\t\n    91\tdef _migration_005_fts5_setup(conn: 
sqlite3.Connection):\n    92\t    """Setup FTS5 virtual table for 
high-performance text search."""\n    93\t    conn.execute(\n    94\t        
"CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5("\n    95\t        "   
content, project, tags, fact_type,"\n    96\t        "    content=\'facts\', 
content_rowid=\'id\'"\n    97\t        ")"\n    98\t    )\n    99\t    # Rebuild
FTS index from existing facts\n   100\t    conn.execute("INSERT INTO 
facts_fts(facts_fts) VALUES(\'rebuild\')")\n   101\t\n   102\t    # Triggers to 
keep FTS5 in sync with facts table\n   103\t    conn.executescript("""\n   104\t
CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN\n   105\t     
INSERT INTO facts_fts(rowid, content, project, tags, fact_type)\n   106\t       
VALUES (new.id, new.content, new.project, new.tags, new.fact_type);\n   107\t   
END;\n   108\t\n   109\t        CREATE TRIGGER IF NOT EXISTS facts_ad AFTER 
DELETE ON facts BEGIN\n   110\t            INSERT INTO facts_fts(facts_fts, 
rowid, content, project, tags, fact_type)\n   111\t            VALUES 
(\'delete\', old.id, old.content, old.project, old.tags, old.fact_type);\n   
112\t        END;\n   113\t\n   114\t        CREATE TRIGGER IF NOT EXISTS 
facts_au AFTER UPDATE ON facts BEGIN\n   115\t            INSERT INTO 
facts_fts(facts_fts, rowid, content, project, tags, fact_type)\n   116\t        
VALUES (\'delete\', old.id, old.content, old.project, old.tags, 
old.fact_type);\n   117\t            INSERT INTO facts_fts(rowid, content, 
project, tags, fact_type)\n   118\t            VALUES (new.id, new.content, 
new.project, new.tags, new.fact_type);\n   119\t        END;\n   120\t    """)\n
121\t    logger.info("Migration 005: Initialized FTS5 search table with sync 
triggers")\n   122\t\n   123\t\n   124\t\n   125\tdef 
_migration_006_graph_memory(conn: sqlite3.Connection):\n   126\t    """Create 
tables for Graph Memory (entity-relationship knowledge graph)."""\n   127\t    
conn.executescript("""\n   128\t        CREATE TABLE IF NOT EXISTS entities (\n 
129\t            id INTEGER PRIMARY KEY AUTOINCREMENT,\n   130\t            name
TEXT NOT NULL,\n   131\t            entity_type TEXT NOT NULL DEFAULT 
\'unknown\',\n   132\t            project TEXT NOT NULL,\n   133\t            
first_seen TEXT NOT NULL,\n   134\t            last_seen TEXT NOT NULL,\n   
135\t            mention_count INTEGER DEFAULT 1,\n   136\t            meta TEXT
DEFAULT \'{}\'\n   137\t        );\n   138\t\n   139\t        CREATE INDEX IF 
NOT EXISTS idx_entities_name_project\n   140\t            ON entities(name, 
project);\n   141\t        CREATE INDEX IF NOT EXISTS idx_entities_type\n   
142\t            ON entities(entity_type);\n   143\t        CREATE INDEX IF NOT 
EXISTS idx_entities_project\n   144\t            ON entities(project);\n   
145\t\n   146\t        CREATE TABLE IF NOT EXISTS entity_relations (\n   147\t  
id INTEGER PRIMARY KEY AUTOINCREMENT,\n   148\t            source_entity_id 
INTEGER NOT NULL REFERENCES entities(id),\n   149\t            target_entity_id 
INTEGER NOT NULL REFERENCES entities(id),\n   150\t            relation_type 
TEXT NOT NULL DEFAULT \'related_to\',\n   151\t            weight REAL DEFAULT 
1.0,\n   152\t            first_seen TEXT NOT NULL,\n   153\t            
source_fact_id INTEGER REFERENCES facts(id)\n   154\t        );\n   155\t\n   
156\t        CREATE INDEX IF NOT EXISTS idx_relations_source\n   157\t          
ON entity_relations(source_entity_id);\n   158\t        CREATE INDEX IF NOT 
EXISTS idx_relations_target\n   159\t            ON 
entity_relations(target_entity_id);\n   160\t    """)\n   161\t    
logger.info("Migration 006: Created Graph Memory tables (entities + 
entity_relations)")\n   162\t\n   163\t\n   164\tdef 
_migration_007_consensus_layer(conn: sqlite3.Connection):\n   165\t    
"""Implement Neural Swarm Consensus (votes + scores)."""\n   166\t    columns = 
{\n   167\t        row[1] for row in conn.execute("PRAGMA 
table_info(facts)").fetchall()\n   168\t    }\n   169\t    if "consensus_score" 
not in columns:\n   170\t        conn.execute("ALTER TABLE facts ADD COLUMN 
consensus_score REAL DEFAULT 1.0")\n   171\t        logger.info("Migration 007: 
Added \'consensus_score\' column to facts")\n   172\t\n   173\t    
conn.executescript("""\n   174\t        CREATE TABLE IF NOT EXISTS 
consensus_votes (\n   175\t            id      INTEGER PRIMARY KEY 
AUTOINCREMENT,\n   176\t            fact_id INTEGER NOT NULL REFERENCES 
facts(id),\n   177\t            agent   TEXT NOT NULL,\n   178\t            vote
INTEGER NOT NULL, -- 1 (verify), -1 (dispute)\n   179\t            timestamp 
TEXT NOT NULL DEFAULT (datetime(\'now\')),\n   180\t            UNIQUE(fact_id, 
agent)\n   181\t        );\n   182\t        CREATE INDEX IF NOT EXISTS 
idx_votes_fact ON consensus_votes(fact_id);\n   183\t    """)\n   184\t    
logger.info("Migration 007: Created \'consensus_votes\' table")\n   185\t\n   
186\t\n   187\tdef _migration_008_consensus_refinement(conn: 
sqlite3.Connection):\n   188\t    """Refine consensus layer: add index and 
ensure referential integrity."""\n   189\t    # Index for preventing Sybil 
lookups and agent vote history\n   190\t    conn.execute(\n   191\t        
"CREATE INDEX IF NOT EXISTS idx_votes_agent ON consensus_votes(agent)"\n   192\t
)\n   193\t    logger.info("Migration 008: Added index on 
consensus_votes(agent)")\n   194\t\n   195\t\n   196\tdef 
_migration_009_reputation_consensus(conn: sqlite3.Connection):\n   197\t    
"""Implement Reputation-Weighted Consensus (RWC) with agents and v2 votes."""\n 
198\t    # 1. Create tables (using scripts from schema.py)\n   199\t    # Note: 
These are \'IF NOT EXISTS\' so safe to run even if schema.py were applied\n   
200\t    from cortex.schema import (\n   201\t        CREATE_AGENTS,\n   202\t  
CREATE_VOTES_V2,\n   203\t        CREATE_TRUST_EDGES,\n   204\t        
CREATE_OUTCOMES,\n   205\t        CREATE_RWC_INDEXES,\n   206\t    )\n   207\t\n
208\t    conn.executescript(CREATE_AGENTS)\n   209\t    
conn.executescript(CREATE_VOTES_V2)\n   210\t    
conn.executescript(CREATE_TRUST_EDGES)\n   211\t    
conn.executescript(CREATE_OUTCOMES)\n   212\t    
conn.executescript(CREATE_RWC_INDEXES)\n   213\t\n   214\t    # 2. Migrate 
existing agents from consensus_votes\n   215\t    # Use hex(randomblob(16)) for 
a simple unique ID\n   216\t    conn.execute("""\n   217\t        INSERT INTO 
agents (id, public_key, name, agent_type, reputation_score)\n   218\t        
SELECT \n   219\t            lower(hex(randomblob(16))),\n   220\t            
\'\',\n   221\t            agent,\n   222\t            \'legacy\',\n   223\t    
0.5\n   224\t        FROM (SELECT DISTINCT agent FROM consensus_votes)\n   225\t
WHERE agent NOT IN (SELECT name FROM agents);\n   226\t    """)\n   227\t\n   
228\t    # 3. Migrate existing votes to v2\n   229\t    conn.execute("""\n   
230\t        INSERT INTO consensus_votes_v2 (\n   231\t            fact_id, 
agent_id, vote, vote_weight, \n   232\t            agent_rep_at_vote, 
created_at\n   233\t        )\n   234\t        SELECT \n   235\t            
v.fact_id,\n   236\t            a.id,\n   237\t            v.vote,\n   238\t    
0.5, -- Initial weight (rep 0.5 * 1.0)\n   239\t            0.5,\n   240\t      
v.timestamp\n   241\t        FROM consensus_votes v\n   242\t        JOIN agents
a ON v.agent = a.name\n   243\t        WHERE NOT EXISTS (\n   244\t            
SELECT 1 FROM consensus_votes_v2 v2 \n   245\t            WHERE v2.fact_id = 
v.fact_id AND v2.agent_id = a.id\n   246\t        );\n   247\t    """)\n   248\t
logger.info("Migration 009: Initialized RWC (agents, votes_v2, outcomes)")\n   
249\t\n   250\t\n   251\t# ─── Migration Registry 
──────────────────────────────────────────────\n   252\t\n   253\tMIGRATIONS = 
[\n   254\t    (1, "Add updated_at column", _migration_001_add_updated_at),\n   
255\t    (2, "Add performance indexes", _migration_002_add_indexes),\n   256\t  
(3, "Enable WAL mode", _migration_003_enable_wal),\n   257\t    (4, "Add IVF 
vector index", _migration_004_vector_index),\n   258\t    (5, "Setup FTS5 
search", _migration_005_fts5_setup),\n   259\t    (6, "Graph Memory tables", 
_migration_006_graph_memory),\n   260\t    (7, "Consensus Layer (votes + 
score)", _migration_007_consensus_layer),\n   261\t    (8, "Consensus refinement
(index)", _migration_008_consensus_refinement),\n   262\t    (9, 
"Reputation-Weighted Consensus", _migration_009_reputation_consensus),\n   
263\t]\n   264\t\n   265\t\n   266\tdef run_migrations(conn: sqlite3.Connection)
-> int:\n   267\t    """Run all pending migrations.\n   268\t\n   269\t    
Args:\n   270\t        conn: SQLite connection.\n   271\t\n   272\t    
Returns:\n   273\t        Number of migrations applied.\n   274\t    """\n   
275\t    from cortex.schema import ALL_SCHEMA\n   276\t\n   277\t    
ensure_migration_table(conn)\n   278\t    current = get_current_version(conn)\n 
279\t    \n   280\t    # Apply base schema if database is fresh (version 0)\n   
281\t    if current == 0:\n   282\t        logger.info("Fresh database detected.
Applying base schema...")\n   283\t        for stmt in ALL_SCHEMA:\n   284\t    
try:\n   285\t                conn.executescript(stmt)\n   286\t            
except (sqlite3.Error, sqlite3.DatabaseError, RuntimeError) as e:\n   287\t     
if "vec0" in str(stmt) or "no such module" in str(e):\n   288\t                 
logger.warning("Skipping schema statement (likely missing vec0): %s", e)\n   
289\t                else:\n   290\t                    raise\n   291\t        
conn.commit()\n   292\t        logger.info("Base schema applied.")\n   293\t    
\n   294\t    applied = 0\n   295\t\n   296\t    for version, description, func 
in MIGRATIONS:\n   297\t        if version > current:\n   298\t            
logger.info("Applying migration %d: %s", version, description)\n   299\t        
try:\n   300\t                func(conn)\n   301\t            except 
(sqlite3.Error, OSError) as e:\n   302\t                logger.error(\n   303\t 
"Migration %d failed: %s. Skipping.", version, e\n   304\t                )\n   
305\t                conn.rollback()\n   306\t                continue\n   307\t
conn.execute(\n   308\t                "INSERT INTO schema_version (version, 
description) VALUES (?, ?)",\n   309\t                (version, description),\n 
310\t            )\n   311\t            conn.commit()\n   312\t            
applied += 1\n   313\t\n   314\t    if applied:\n   315\t        
logger.info("Applied %d migration(s). Schema now at version %d",\n   316\t      
applied, get_current_version(conn))\n   317\t    return applied\n',
        message='317 lines read from file starting from line 1. End of file 
reached.',
        display=[],
        extras=None
    )
)
ToolCallPart(
    arguments_part='nandezangulo/cortex/kimi_architectural_analysis.md", 
"n_lines": 200}'
)
ToolCall(
    type='function',
    id='tool_xPJWE1Uux4FEDhighBmxyrf4',
    function=FunctionBody(name='Glob', arguments='{"pattern": "tests/*.py"}'),
    extras=None
)
ToolResult(
    tool_call_id='tool_9MNCXl4YSIhSqfmGldbPfzvW',
    return_value=ToolOk(
        is_error=False,
        output='     1\t# Análisis Arquitectónico: Sistema de Consenso CORTEX 
v4.0\n     2\t## Evaluación hacia Reputation-Weighted Consensus para Sovereign 
AI\n     3\t\n     4\t**Fecha:** 2026-02-16  \n     5\t**Versión Analizada:** 
4.0.0a1  \n     6\t**Autor:** Análisis Automatizado Kimi Code CLI  \n     7\t\n 
8\t---\n     9\t\n    10\t## 1. Sistema de Consenso Actual (Neural Swarm 
Consensus)\n    11\t\n    12\t### 1.1 Implementación Actual\n    13\t\n    
14\t```python\n    15\t# cortex/engine.py:468-494\n    16\tdef 
_recalculate_consensus(self, fact_id: int, conn: sqlite3.Connection) -> float:\n
17\t    """Update consensus_score based on votes and adjust confidence."""\n    
18\t    row = conn.execute(\n    19\t        "SELECT SUM(vote) FROM 
consensus_votes WHERE fact_id = ?",\n    20\t        (fact_id,),\n    21\t    
).fetchone()\n    22\t    vote_sum = row[0] or 0\n    23\t    score = 1.0 + 
(vote_sum * 0.1)  # ← Fórmula lineal simple\n    24\t\n    25\t    # Thresholds 
for automatic confidence shifting\n    26\t    new_confidence = None\n    27\t  
if score >= 1.5:\n    28\t        new_confidence = "verified"\n    29\t    elif 
score <= 0.5:\n    30\t        new_confidence = "disputed"\n    31\t    # ...\n 
32\t```\n    33\t\n    34\t### 1.2 Esquema de Base de Datos Actual\n    35\t\n  
36\t```sql\n    37\t-- Tabla de votos (consensus_votes)\n    38\tCREATE TABLE 
consensus_votes (\n    39\t    id          INTEGER PRIMARY KEY AUTOINCREMENT,\n 
40\t    fact_id     INTEGER NOT NULL REFERENCES facts(id),\n    41\t    agent   
TEXT NOT NULL,           -- ← Simple string, no FK\n    42\t    vote        
INTEGER NOT NULL,        -- 1 (verify), -1 (dispute)\n    43\t    timestamp   
TEXT NOT NULL DEFAULT (datetime(\'now\')),\n    44\t    UNIQUE(fact_id, agent)\n
45\t);\n    46\t\n    47\t-- Tabla de facts con score\n    48\tCREATE TABLE 
facts (\n    49\t    id               INTEGER PRIMARY KEY AUTOINCREMENT,\n    
50\t    -- ... campos existentes ...\n    51\t    consensus_score  REAL DEFAULT 
1.0,   -- ← Score agregado\n    52\t    confidence       TEXT DEFAULT 
\'stated\'\n    53\t);\n    54\t```\n    55\t\n    56\t### 1.3 Características 
del Sistema Lineal\n    57\t\n    58\t| Aspecto | Implementación | Implicación 
|\n    59\t|---------|---------------|-------------|\n    60\t| **Peso del 
voto** | 1.0 para todos los agentes | Democracia pura, vulnerable a Sybil 
attacks |\n    61\t| **Fórmula** | `1.0 + sum(votos) * 0.1` | Lineal, sin 
decaimiento temporal |\n    62\t| **Umbral verified** | ≥ 1.5 (5 votos 
positivos) | Fijo, no adaptativo |\n    63\t| **Umbral disputed** | ≤ 0.5 (5 
votos negativos) | Fijo, no adaptativo |\n    64\t| **Identidad de agente** | 
TEXT libre | Sin verificación criptográfica |\n    65\t| **Historial** | No 
existe | Cada voto es independiente |\n    66\t\n    67\t---\n    68\t\n    
69\t## 2. Evaluación de Adequación para Sovereign AI\n    70\t\n    71\t### 2.1 
Vulnerabilidades Críticas del Sistema Lineal\n    72\t\n    73\t#### Ataque 
Sybil (Identidades Múltiples)\n    74\t```\n    75\tEscenario: Agente malicioso 
crea 100 identidades (agent_1 ... agent_100)\n    76\t\n    77\tAtaque: Cada 
identidad vota +1 en "facts" falsos promovidos por el atacante\n    78\t        
y -1 en facts legítimos de competidores.\n    79\t\n    80\tImpacto: Con 100 
identidades, el atacante puede:\n    81\t  - Verificar cualquier fact falso con 
10 votos propios\n    82\t  - Disputar cualquier fact legítimo con 10 votos 
propios\n    83\t  \n    84\tCosto: Cero. No hay staking, no hay costo de 
identidad, no hay validación.\n    85\t```\n    86\t\n    87\t#### Ataque de 
Voto a Largo Plazo\n    88\t```\n    89\tEscenario: Agente con historial 
perfecto de 1000 votos correctos\n    90\t\n    91\tProblema: En el sistema 
actual, ese agente tiene el mismo peso que uno nuevo.\n    92\t          No hay 
acumulación de reputación.\n    93\t\n    94\tPérdida: Incentivos alineados 
incorrectamente. Los agentes con mejor track\n    95\t         record no tienen 
mayor influencia en el consenso.\n    96\t```\n    97\t\n    98\t#### Ataque de 
"Voto Fantasma"\n    99\t```\n   100\tEscenario: Agentes inactivos mantienen 
votos históricos indefinidamente\n   101\t\n   102\tProblema: El sistema no 
tiene decay temporal. Un voto de hace 1 año tiene\n   103\t          el mismo 
peso que uno de ayer.\n   104\t\n   105\tImpacto: El consenso no refleja el 
estado actual de conocimiento del swarm.\n   106\t```\n   107\t\n   108\t### 2.2
Comparativa con Sistemas de Consenso Reputacionales\n   109\t\n   110\t| Sistema
| Mecanismo de Reputación | Resistencia Sybil | Aplicabilidad a CORTEX |\n   
111\t|---------|------------------------|-------------------|-------------------
-----|\n   112\t| **CORTEX Actual** | Ninguno | ❌ Ninguna | Baseline |\n   
113\t| **PageRank (Google)** | Links entrantes/salientes | ⚠️ Parcial | Adaptable
|\n   114\t| **EigenTrust (P2P)** | Trust transitivity | ⚠️ Media | Alta |\n   
115\t| **RepSys (BitTorrent)** | Ratio upload/download | ✅ Alta | Media |\n   
116\t| **Token-Curated Registry** | Staking económico | ✅ Muy alta | Requiere 
token |\n   117\t| **Bonding Curves** | Stake + tiempo | ✅ Muy alta | Adaptable
|\n   118\t\n   119\t### 2.3 Veredicto: ¿Es Suficiente el Sistema Lineal?\n   
120\t\n   121\t**RESPUESTA: NO.** Para una Sovereign AI con autonomía real, el 
sistema actual es **inadecuado** por:\n   122\t\n   123\t1. **Falta de 
resistencia a Sybil attacks** — Cualquier entidad puede crear infinitas 
identidades\n   124\t2. **Sin memoria histórica** — No distingue entre agentes 
confiables y nuevos\n   125\t3. **Sin decay temporal** — Votos antiguos 
perpetúan el consenso sin revisión\n   126\t4. **Sin staking o costo de 
oportunidad** — Votar es gratuito, no hay consecuencias por votar mal\n   
127\t5. **Sin mecanismo de slashing** — Agentes maliciosos no pierden 
reputación\n   128\t\n   129\t---\n   130\t\n   131\t## 3. Propuesta: 
Reputation-Weighted Consensus (RWC)\n   132\t\n   133\t### 3.1 Principios de 
Diseño\n   134\t\n   135\t```\n   
136\t┌─────────────────────────────────────────────────────────────────────────┐
\n   137\t│                    REPUTATION-WEIGHTED CONSENSUS                    
│\n   
138\t├─────────────────────────────────────────────────────────────────────────┤
\n   139\t│                                                                     
│\n   140\t│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐       
│\n   141\t│   │   AGENTE A   │     │   AGENTE B   │     │   AGENTE C   │       
│\n   142\t│   │  Rep: 0.95   │     │  Rep: 0.45   │     │  Rep: 0.12   │       
│\n   143\t│   │  Voto: +1    │     │  Voto: +1    │     │  Voto: -1    │       
│\n   144\t│   └──────┬───────┘     └──────┬───────┘     └──────┬───────┘       
│\n   145\t│          │                    │                    │               
│\n   146\t│          ▼                    ▼                    ▼               
│\n   147\t│       Peso: 0.95           Peso: 0.45           Peso: 0.12         
│\n   148\t│                                                                    
│\n   149\t│          └────────────────────┬────────────────────┘               
│\n   150\t│                               ▼                                    
│\n   151\t│                    Score = Σ(votoᵢ × repᵢ × decayᵢ)                
│\n   152\t│                                                                    
│\n   153\t│                    Score = (1×0.95×1.0) + (1×0.45×1.0)             
│\n   154\t│                             + (-1×0.12×1.0)                        
│\n   155\t│                                                                    
│\n   156\t│                    Score = 0.95 + 0.45 - 0.12 = 1.28               
│\n   157\t│                                                                    
│\n   
158\t└─────────────────────────────────────────────────────────────────────────┘
\n   159\t```\n   160\t\n   161\t### 3.2 Esquema de Base de Datos Evolucionado\n
162\t\n   163\t#### Tabla Principal: `agents` (Nueva)\n   164\t\n   
165\t```sql\n   166\t-- =====================================================\n 
167\t-- AGENT REGISTRY - Identidades verificables del swarm\n   168\t-- 
=====================================================\n   169\tCREATE TABLE 
agents (\n   170\t    -- Identidad\n   171\t    id              TEXT PRIMARY 
KEY,           -- UUID v4 o DID (Decentralized ID)\n   172\t    public_key      
TEXT NOT NULL,              -- Clave pública para verificación\n   173\t    \n  
174\t    -- Metadata\n   175\t    name            TEXT NOT NULL,\n   176\t    
agent_type      TEXT NOT NULL DEFAULT \'ai\', -- \'ai\', \'human\', \'oracle\', 
\'system\'\n   177\t    tenant_id       TEXT NOT NULL DEFAULT \'default\',\n   
178\t    created_at      TEXT NOT NULL DEFAULT (datetime(\'now\')),\n   179\t   
\n   180\t    -- Reputación Acumulada (Time-Decayed EMA)\n   181\t    
reputation_score    REAL NOT NULL DEFAULT 0.5,  -- Range [0.0, 1.0]\n   182\t   
reputation_stake    REAL NOT NULL DEFAULT 0.0,  -- Stake económico (si aplica)\n
183\t    \n   184\t    -- Métricas de Performance\n   185\t    total_votes      
INTEGER DEFAULT 0,\n   186\t    successful_votes    INTEGER DEFAULT 0,      -- 
Votos que alinearon con consenso final\n   187\t    disputed_votes      INTEGER 
DEFAULT 0,      -- Votos en facts que fueron disputados\n   188\t    \n   189\t 
-- Decay Temporal (última actividad)\n   190\t    last_active_at      TEXT NOT 
NULL DEFAULT (datetime(\'now\')),\n   191\t    \n   192\t    -- Estado\n   193\t
is_active           BOOLEAN DEFAULT TRUE,\n   194\t    is_verified         
BOOLEAN DEFAULT FALSE,  -- Verificación KYC/oracle\n   195\t    \n   196\t    --
JSON para extensibilidad\n   197\t    meta                TEXT DEFAULT \'{}\'\n 
198\t);\n   199\t\n   200\t-- Índices críticos\n',
        message='200 lines read from file starting from line 1.',
        display=[],
        extras=None
    )
)
StatusUpdate(
    context_usage=0.182373046875,
    token_usage=TokenUsage(
        input_other=19392,
        output=104,
        input_cache_read=28416,
        input_cache_creation=0
    ),
    message_id='chatcmpl-9mpiPaQRBAB3pICulYAxn3k9'
)
ToolResult(
    tool_call_id='tool_xPJWE1Uux4FEDhighBmxyrf4',
    return_value=ToolOk(
        is_error=False,
        output='tests/__init__.py\ntests/test_api.py\ntests/test_auth.py\ntests/
test_cli_crud.py\ntests/test_consensus.py\ntests/test_consensus_security.py\ntes
ts/test_daemon.py\ntests/test_daemon_cli.py\ntests/test_dashboard.py\ntests/test
_engine.py\ntests/test_graph.py\ntests/test_hardening.py\ntests/test_improvement
s.py\ntests/test_mcp_server.py\ntests/test_mejoralo_round2.py\ntests/test_mejora
lo_round6.py\ntests/test_mejoralo_round7.py\ntests/test_mejoralo_round8.py\ntest
s/test_mejoralo_rounds3_5.py\ntests/test_search.py\ntests/test_security_hardenin
g.py\ntests/test_sync.py\ntests/test_temporal.py\ntests/test_timing.py\ntests/ve
rify_security.py',
        message='Found 25 matches for pattern `tests/*.py`.',
        display=[],
        extras=None
    )
)
StepBegin(n=4)
TextPart(
    type='text',
    text='Now I have a comprehensive understanding of the CORTEX V4.0 
architecture. Let me create a detailed Wave 5 proposal document that addresses 
the three key areas:'
)
ToolCall(
    type='function',
    id='tool_b7WYr4NsQbCY79yp0ZWmrZQU',
    function=FunctionBody(
        name='SetTodoList',
        arguments='{"todos": [{"title": "Analyze current architecture and 
consensus layer", "status": "done"}, {"title": "Design Wave 5: Immutable Vote 
Logging", "status": "in_progress"}, {"title": "Design Wave 5: HA Ledger 
Synchronization", "status": "pending"}, {"title": "Design Wave 5: MCP Server 
Edge Optimization", "status": "pending"}, {"title": "Create comprehensive Wave 5
proposal document", "status": "pending"}]}'
    ),
    extras=None
)
ToolResult(
    tool_call_id='tool_b7WYr4NsQbCY79yp0ZWmrZQU',
    return_value=ToolReturnValue(
        is_error=False,
        output='',
        message='Todo list updated',
        display=[
            TodoDisplayBlock(
                type='todo',
                items=[
                    TodoDisplayItem(
                        title='Analyze current architecture and consensus 
layer',
                        status='done'
                    ),
                    TodoDisplayItem(
                        title='Design Wave 5: Immutable Vote Logging',
                        status='in_progress'
                    ),
                    TodoDisplayItem(
                        title='Design Wave 5: HA Ledger Synchronization',
                        status='pending'
                    ),
                    TodoDisplayItem(
                        title='Design Wave 5: MCP Server Edge Optimization',
                        status='pending'
                    ),
                    TodoDisplayItem(
                        title='Create comprehensive Wave 5 proposal document',
                        status='pending'
                    )
                ]
            )
        ],
        extras=None
    )
)
StatusUpdate(
    context_usage=0.20869064331054688,
    token_usage=TokenUsage(
        input_other=7091,
        output=147,
        input_cache_read=47616,
        input_cache_creation=0
    ),
    message_id='chatcmpl-7CPavceiiL4FW8TdlhDNxLW1'
)
StepBegin(n=5)
ToolCall(
    type='function',
    id='tool_QoKduwydVKveVVrBw2bLTOS0',
    function=FunctionBody(
        name='WriteFile',
        arguments='{"path": 
"/Users/borjafernandezangulo/cortex/WAVE5_PROPOSAL_PERSISTENCE_DEPLOYMENT.md", 
"content": "# CORTEX V4.0 — Wave 5: Persistence & Deployment\\n## 
Production-Ready Consensus Infrastructure\\n\\n**Date:** 2026-02-16  
\\n**Version:** 5.0.0-proposal  \\n**Status:** Technical Design Document  
\\n**Author:** CORTEX Architecture Team  \\n\\n---\\n\\n## Executive 
Summary\\n\\nWave 5 transforms CORTEX from a development-ready system into a 
**production-grade sovereign memory infrastructure**. Building upon the 
Reputation-Weighted Consensus (RWC) foundation from Wave 4, this wave delivers 
three critical capabilities:\\n\\n1. **Immutable Vote Logging** — 
Cryptographically tamper-evident consensus audit trail\\n2. **High-Availability 
Ledger Synchronization** — Multi-node consensus with conflict-free 
replication\\n3. **Edge-Optimized MCP Server** — High-performance Model Context 
Protocol for distributed deployments\\n\\n### Wave Completion Status\\n\\n| Wave
| Feature | Status |\\n|------|---------|--------|\\n| Wave 1 | Core Engine 
(Facts, Search, Embeddings) | ✅ Complete |\\n| Wave 2 | Temporal Facts & 
Transaction Ledger | ✅ Complete |\\n| Wave 3 | REST API, Auth, Dashboard | ✅ 
Complete |\\n| Wave 4 | Consensus Layer (RWC) | ✅ Complete |\\n| **Wave 5** | 
**Persistence & Deployment** | 🔄 **Proposed** |\\n| Wave 6 | Swarm Federation &
Bridge Protocols | 📋 Planned |\\n\\n---\\n\\n## 1. Immutable Vote 
Logging\\n\\n### 1.1 Problem Statement\\n\\nThe current consensus system has 
critical audit gaps:\\n\\n```python\\n# Current Implementation (Wave 4)\\n# 
Votes are stored but NOT linked to the immutable ledger\\nconn.execute(\\n    
\\"INSERT INTO consensus_votes_v2 (fact_id, agent_id, vote, vote_weight) 
...\\"\\n)\\n# No cryptographic proof of vote existence\\n# No protection 
against \\"God Key\\" database admin attacks\\n# No external 
verifiability\\n```\\n\\n**Vulnerabilities:**\\n- ❌ Votes can be modified by 
database administrators\\n- ❌ No cryptographic proof of vote 
ordering/timing\\n- ❌ No mechanism for external audit\\n- ❌ Vote history can 
be selectively deleted\\n\\n### 1.2 Design Goals\\n\\n| Goal | Priority | 
Description |\\n|------|----------|-------------|\\n| **Tamper-Proof** | P0 | 
Cryptographic guarantees against any modification |\\n| **Verifiable** | P0 | 
Third parties can verify integrity without trust |\\n| **Ordered** | P0 | Strict
temporal ordering of all votes |\\n| **Efficient** | P1 | <5ms overhead per vote
|\\n| **Exportable** | P1 | JSON/CSV export for external auditors |\\n| 
**Redundant** | P2 | Multiple storage backends (local + remote hash log) 
|\\n\\n### 1.3 Architecture: Hierarchical Vote 
Ledger\\n\\n```\\n┌─────────────────────────────────────────────────────────────
────────────────┐\\n│                    IMMUTABLE VOTE LEDGER ARCHITECTURE     
│\\n├───────────────────────────────────────────────────────────────────────────
──┤\\n│                                                                         
     │\\n│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐         
│\\n│   │  Vote Cast   │────▶│  Vote Entry  │────▶│  Hash Chain  │              
│\\n│   │   (Event)    │     │  (SQLite)    │     │  (SHA-256)   │              
│\\n│   └──────────────┘     └──────────────┘     └──────┬───────┘              
│\\n│                                                     │                     
│\\n│                              ┌──────────────────────┘                     
│\\n│                              ▼                                            
│\\n│   ┌────────────────────────────────────────────────────────────┐          
│\\n│   │              MERKLE TREE LAYER (Batched)                    │         
│\\n│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │          
│\\n│   │  │  Batch 1    │  │  Batch 2    │  │  Batch N    │         │          
│\\n│   │  │  Root: 0x.. │  │  Root: 0x.. │  │  Root: 0x.. │         │          
│\\n│   │  │  1000 votes │  │  1000 votes │  │  1000 votes │         │          
│\\n│   │  └─────────────┘  └─────────────┘  └─────────────┘         │          
│\\n│   └────────────────────────────────────────────────────────────┘          
│\\n│                              │                                            
│\\n│                              ▼                                            
│\\n│   ┌────────────────────────────────────────────────────────────┐          
│\\n│   │              EXTERNAL SIGNATURE LAYER (Optional)            │         
│\\n│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │          
│\\n│   │  │  Signify    │  │  OpenPubKey │  │  Anchoring  │         │          
│\\n│   │  │  (Sigstore) │  │  (SSH/PGP)  │  │  (Optional) │         │          
│\\n│   │  └─────────────┘  └─────────────┘  └─────────────┘         │          
│\\n│   └────────────────────────────────────────────────────────────┘          
│\\n│                                                                           
│\\n└───────────────────────────────────────────────────────────────────────────
──┘\\n```\\n\\n### 1.4 Database Schema Extensions\\n\\n```sql\\n-- 
============================================================\\n-- MIGRATION 010:
Immutable Vote Ledger\\n-- 
============================================================\\n\\n-- Vote 
ledger: Append-only, hash-chained record of all votes\\nCREATE TABLE vote_ledger
(\\n    id              INTEGER PRIMARY KEY AUTOINCREMENT,\\n    \\n    -- Vote 
reference\\n    fact_id         INTEGER NOT NULL REFERENCES facts(id),\\n    
agent_id        TEXT NOT NULL REFERENCES agents(id),\\n    vote            
INTEGER NOT NULL,  -- +1 (verify), -1 (dispute)\\n    vote_weight     REAL NOT 
NULL,\\n    \\n    -- Cryptographic chain\\n    prev_hash       TEXT NOT NULL,  
-- Previous vote ledger entry hash\\n    hash            TEXT NOT NULL,      -- 
SHA-256 of this entry\\n    \\n    -- Temporal proof\\n    timestamp       TEXT 
NOT NULL DEFAULT (datetime(\'now\')),\\n    \\n    -- Optional: External 
verification\\n    signature       TEXT,               -- Ed25519 signature by 
agent\\n    \\n    -- Index for efficient verification\\n    
UNIQUE(hash)\\n);\\n\\nCREATE INDEX idx_vote_ledger_fact ON 
vote_ledger(fact_id);\\nCREATE INDEX idx_vote_ledger_agent ON 
vote_ledger(agent_id);\\nCREATE INDEX idx_vote_ledger_timestamp ON 
vote_ledger(timestamp);\\n\\n-- Merkle tree roots for periodic integrity 
verification\\nCREATE TABLE vote_merkle_roots (\\n    id              INTEGER 
PRIMARY KEY AUTOINCREMENT,\\n    root_hash       TEXT NOT NULL,              -- 
SHA-256 of combined vote hashes\\n    vote_start_id   INTEGER NOT NULL,         
-- First vote in this batch\\n    vote_end_id     INTEGER NOT NULL,           --
Last vote in this batch\\n    vote_count      INTEGER NOT NULL,\\n    created_at
TEXT NOT NULL DEFAULT (datetime(\'now\')),\\n    \\n    -- Optional: External 
proof-of-existence\\n    external_proof  TEXT,                       -- URL or 
hash of external anchor\\n    \\n    -- Signature by \\"God Key\\" (if 
configured)\\n    signature       TEXT                        -- Ed25519 
signature of root_hash\\n);\\n\\nCREATE INDEX idx_vote_merkle_range ON 
vote_merkle_roots(vote_start_id, vote_end_id);\\n\\n-- Audit log export 
tracking\\nCREATE TABLE vote_audit_exports (\\n    id              INTEGER 
PRIMARY KEY AUTOINCREMENT,\\n    export_type     TEXT NOT NULL,              -- 
\'json\', \'csv\', \'chain\'\\n    filename        TEXT NOT NULL,\\n    
file_hash       TEXT NOT NULL,              -- SHA-256 of exported file\\n    
vote_start_id   INTEGER NOT NULL,\\n    vote_end_id     INTEGER NOT NULL,\\n    
exported_at     TEXT NOT NULL DEFAULT (datetime(\'now\')),\\n    exported_by    
TEXT NOT NULL               -- API key or agent ID\\n);\\n\\n-- Tamper detection
log (append-only by design)\\nCREATE TABLE vote_integrity_checks (\\n    id     
INTEGER PRIMARY KEY AUTOINCREMENT,\\n    check_type      TEXT NOT NULL,         
-- \'merkle\', \'chain\', \'full\'\\n    status          TEXT NOT NULL,         
-- \'ok\', \'violation\', \'error\'\\n    details         TEXT,                 
-- JSON with findings\\n    started_at      TEXT NOT NULL,\\n    completed_at   
TEXT NOT NULL\\n);\\n```\\n\\n### 1.5 Implementation: Immutable Vote 
Ledger\\n\\n```python\\n# cortex/vote_ledger.py\\n\\"\\"\\"\\nImmutable Vote 
Ledger — Cryptographic integrity for CORTEX consensus votes.\\n\\nFeatures:\\n- 
Hash-chained vote entries\\n- Periodic Merkle tree generation\\n- Tamper 
detection via hash verification\\n- Export with integrity 
proofs\\n\\"\\"\\"\\n\\nimport hashlib\\nimport json\\nimport sqlite3\\nfrom 
typing import List, Optional, Tuple\\nfrom dataclasses import dataclass\\nfrom 
datetime import datetime\\n\\n\\n@dataclass\\nclass VoteEntry:\\n    \\"\\"\\"A 
single entry in the vote ledger.\\"\\"\\"\\n    id: int\\n    fact_id: int\\n   
agent_id: str\\n    vote: int\\n    vote_weight: float\\n    prev_hash: str\\n  
hash: str\\n    timestamp: str\\n    signature: Optional[str] = 
None\\n\\n\\nclass VoteLedger:\\n    \\"\\"\\"\\n    Manages the cryptographic 
integrity of CORTEX consensus votes.\\n    \\n    Features:\\n    - Append-only 
hash-chained vote storage\\n    - Periodic Merkle tree generation\\n    - Tamper
detection via hash verification\\n    - Export with integrity proofs\\n    
\\"\\"\\"\\n    \\n    MERKLE_BATCH_SIZE = 1000  # Create Merkle root every N 
votes\\n    \\n    def __init__(self, conn: sqlite3.Connection):\\n        
self.conn = conn\\n    \\n    def _compute_hash(\\n        self,\\n        
prev_hash: str,\\n        fact_id: int,\\n        agent_id: str,\\n        vote:
int,\\n        vote_weight: float,\\n        timestamp: str\\n    ) -> str:\\n  
\\"\\"\\"Compute the hash for a vote entry.\\"\\"\\"\\n        hash_input = 
f\\"{prev_hash}:{fact_id}:{agent_id}:{vote}:{vote_weight}:{timestamp}\\"\\n     
return hashlib.sha256(hash_input.encode()).hexdigest()\\n    \\n    def 
append_vote(\\n        self,\\n        fact_id: int,\\n        agent_id: str,\\n
vote: int,\\n        vote_weight: float,\\n        signature: Optional[str] = 
None\\n    ) -> VoteEntry:\\n        \\"\\"\\"\\n        Append a vote to the 
immutable ledger.\\n        \\n        Args:\\n            fact_id: The fact 
being voted on\\n            agent_id: The voting agent\\n            vote: +1 
(verify) or -1 (dispute)\\n            vote_weight: The weight of the vote 
(reputation-based)\\n            signature: Optional cryptographic signature\\n 
\\n        Returns:\\n            The created VoteEntry with computed hash\\n   
\\"\\"\\"\\n        # Get previous hash\\n        prev = self.conn.execute(\\n  
\\"SELECT hash FROM vote_ledger ORDER BY id DESC LIMIT 1\\"\\n        
).fetchone()\\n        prev_hash = prev[0] if prev else \\"GENESIS\\"\\n        
\\n        # Compute timestamp\\n        timestamp = 
datetime.utcnow().isoformat()\\n        \\n        # Compute hash\\n        
entry_hash = self._compute_hash(\\n            prev_hash, fact_id, agent_id, 
vote, vote_weight, timestamp\\n        )\\n        \\n        # Insert vote 
entry\\n        cursor = self.conn.execute(\\n            \\"\\"\\"\\n          
INSERT INTO vote_ledger \\n            (fact_id, agent_id, vote, vote_weight, 
prev_hash, hash, timestamp, signature)\\n            VALUES (?, ?, ?, ?, ?, ?, 
?, ?)\\n            \\"\\"\\",\\n            (fact_id, agent_id, vote, 
vote_weight, prev_hash, entry_hash, timestamp, signature)\\n        )\\n        
\\n        # Check if we need to create a Merkle checkpoint\\n        
self._maybe_create_checkpoint()\\n        \\n        return VoteEntry(\\n       
id=cursor.lastrowid,\\n            fact_id=fact_id,\\n            
agent_id=agent_id,\\n            vote=vote,\\n            
vote_weight=vote_weight,\\n            prev_hash=prev_hash,\\n            
hash=entry_hash,\\n            timestamp=timestamp,\\n            
signature=signature\\n        )\\n    \\n    def _maybe_create_checkpoint(self) 
-> Optional[int]:\\n        \\"\\"\\"Create a Merkle checkpoint if batch size is
reached.\\"\\"\\"\\n        # Count votes since last checkpoint\\n        last =
self.conn.execute(\\n            \\"SELECT MAX(vote_end_id) FROM 
vote_merkle_roots\\"\\n        ).fetchone()[0] or 0\\n        \\n        count =
self.conn.execute(\\n            \\"SELECT COUNT(*) FROM vote_ledger WHERE id > 
?\\",\\n            (last,)\\n        ).fetchone()[0]\\n        \\n        if 
count < self.MERKLE_BATCH_SIZE:\\n            return None\\n        \\n        
return self.create_merkle_checkpoint()\\n    \\n    def 
create_merkle_checkpoint(self) -> Optional[int]:\\n        \\"\\"\\"\\n        
Create a Merkle tree checkpoint for recent votes.\\n        Returns the 
checkpoint ID or None if no new votes.\\n        \\"\\"\\"\\n        # Find last
checkpoint\\n        last = self.conn.execute(\\n            \\"SELECT 
MAX(vote_end_id) FROM vote_merkle_roots\\"\\n        ).fetchone()[0] or 0\\n    
\\n        # Get range of votes to include\\n        start = last + 1\\n        
end_row = self.conn.execute(\\n            \\"SELECT id FROM vote_ledger WHERE 
id > ? ORDER BY id LIMIT 1 OFFSET ?\\",\\n            (last, 
self.MERKLE_BATCH_SIZE - 1)\\n        ).fetchone()\\n        end = end_row[0] if
end_row else start\\n        \\n        # Compute Merkle root\\n        root = 
self._compute_merkle_root(start, end)\\n        if not root:\\n            
return None\\n        \\n        # Store checkpoint\\n        cursor = 
self.conn.execute(\\n            \\"\\"\\"INSERT INTO vote_merkle_roots \\n     
(root_hash, vote_start_id, vote_end_id, vote_count) \\n                VALUES 
(?, ?, ?, ?)\\"\\"\\",\\n            (root, start, end, end - start + 1)\\n     
)\\n        \\n        return cursor.lastrowid\\n    \\n    def 
_compute_merkle_root(self, start_id: int, end_id: int) -> Optional[str]:\\n     
\\"\\"\\"Compute Merkle root for a range of votes.\\"\\"\\"\\n        cursor = 
self.conn.execute(\\n            \\"SELECT hash FROM vote_ledger WHERE id >= ? 
AND id <= ? ORDER BY id\\",\\n            (start_id, end_id)\\n        )\\n     
hashes = [row[0] for row in cursor.fetchall()]\\n        \\n        if not 
hashes:\\n            return None\\n        \\n        # Build Merkle tree\\n   
while len(hashes) > 1:\\n            next_level = []\\n            for i in 
range(0, len(hashes), 2):\\n                left = hashes[i]\\n                
right = hashes[i + 1] if i + 1 < len(hashes) else hashes[i]\\n                
combined = hashlib.sha256((left + right).encode()).hexdigest()\\n               
next_level.append(combined)\\n            hashes = next_level\\n        \\n     
return hashes[0]\\n    \\n    def verify_chain_integrity(self) -> dict:\\n      
\\"\\"\\"\\n        Verify the integrity of the entire vote ledger.\\n        
\\n        Returns:\\n            Dict with verification results\\n        
\\"\\"\\"\\n        violations = []\\n        \\n        # 1. Verify hash chain 
continuity\\n        votes = self.conn.execute(\\n            \\"SELECT id, 
prev_hash, hash, fact_id, agent_id, vote, vote_weight, timestamp \\"\\n         
\\"FROM vote_ledger ORDER BY id\\"\\n        ).fetchall()\\n        \\n        
prev_hash = \\"GENESIS\\"\\n        for vote in votes:\\n            vote_id, 
tx_prev, tx_hash, fact_id, agent_id, vote_val, weight, ts = vote\\n            
\\n            # Verify prev_hash matches\\n            if tx_prev != 
prev_hash:\\n                violations.append({\\n                    
\\"vote_id\\": vote_id,\\n                    \\"type\\": \\"chain_break\\",\\n 
\\"expected_prev\\": prev_hash,\\n                    \\"actual_prev\\": 
tx_prev\\n                })\\n            \\n            # Verify current 
hash\\n            computed = self._compute_hash(\\n                tx_prev, 
fact_id, agent_id, vote_val, weight, ts\\n            )\\n            \\n       
if computed != tx_hash:\\n                violations.append({\\n                
\\"vote_id\\": vote_id,\\n                    \\"type\\": 
\\"hash_mismatch\\",\\n                    \\"computed\\": computed,\\n         
\\"stored\\": tx_hash\\n                })\\n            \\n            
prev_hash = tx_hash\\n        \\n        # 2. Verify Merkle roots\\n        
merkles = self.conn.execute(\\n            \\"SELECT id, root_hash, 
vote_start_id, vote_end_id FROM vote_merkle_roots ORDER BY id\\"\\n        
).fetchall()\\n        \\n        for m in merkles:\\n            m_id, 
stored_root, start, end = m\\n            computed_root = 
self._compute_merkle_root(start, end)\\n            \\n            if 
computed_root != stored_root:\\n                violations.append({\\n          
\\"merkle_id\\": m_id,\\n                    \\"type\\": 
\\"merkle_mismatch\\",\\n                    \\"range\\": 
f\\"{start}-{end}\\",\\n                    \\"computed\\": computed_root,\\n   
\\"stored\\": stored_root\\n                })\\n        \\n        return {\\n 
\\"valid\\": len(violations) == 0,\\n            \\"violations\\": 
violations,\\n            \\"votes_checked\\": len(votes),\\n            
\\"merkle_roots_checked\\": len(merkles)\\n        }\\n    \\n    def 
get_vote_history(self, fact_id: int) -> List[VoteEntry]:\\n        \\"\\"\\"Get 
the complete vote history for a fact.\\"\\"\\"\\n        cursor = 
self.conn.execute(\\n            \\"SELECT id, fact_id, agent_id, vote, 
vote_weight, prev_hash, hash, timestamp, signature \\"\\n            \\"FROM 
vote_ledger WHERE fact_id = ? ORDER BY id\\",\\n            (fact_id,)\\n       
)\\n        \\n        return [\\n            VoteEntry(\\n                
id=row[0],\\n                fact_id=row[1],\\n                
agent_id=row[2],\\n                vote=row[3],\\n                
vote_weight=row[4],\\n                prev_hash=row[5],\\n                
hash=row[6],\\n                timestamp=row[7],\\n                
signature=row[8]\\n            )\\n            for row in cursor.fetchall()\\n  
]\\n    \\n    def export_verifiable_log(self, output_path: str, start_id: int =
1) -> dict:\\n        \\"\\"\\"\\n        Export votes with integrity proofs.\\n
\\n        Args:\\n            output_path: Where to write the export (JSON 
format)\\n            start_id: Starting vote ID\\n            \\n        
Returns:\\n            Export metadata with root hash for verification\\n       
\\"\\"\\"\\n        votes = self.conn.execute(\\n            \\"SELECT * FROM 
vote_ledger WHERE id >= ? ORDER BY id\\",\\n            (start_id,)\\n        
).fetchall()\\n        \\n        # Build Merkle tree\\n        hashes = [v[6] 
for v in votes]  # hash column\\n        \\n        # Compute root\\n        
root = hashes[0] if hashes else None\\n        while len(hashes) > 1:\\n        
next_level = []\\n            for i in range(0, len(hashes), 2):\\n             
left = hashes[i]\\n                right = hashes[i + 1] if i + 1 < len(hashes) 
else hashes[i]\\n                combined = hashlib.sha256((left + 
right).encode()).hexdigest()\\n                next_level.append(combined)\\n   
hashes = next_level\\n            root = hashes[0] if hashes else None\\n       
\\n        export_data = {\\n            \\"export\\": {\\n                
\\"version\\": \\"1.0\\",\\n                \\"exported_at\\": 
datetime.utcnow().isoformat(),\\n                \\"start_id\\": start_id,\\n   
\\"end_id\\": votes[-1][0] if votes else start_id,\\n                
\\"vote_count\\": len(votes),\\n                \\"merkle_root\\": root\\n      
},\\n            \\"votes\\": [\\n                {\\n                    
\\"id\\": v[0],\\n                    \\"fact_id\\": v[1],\\n                   
\\"agent_id\\": v[2],\\n                    \\"vote\\": v[3],\\n                
\\"vote_weight\\": v[4],\\n                    \\"prev_hash\\": v[5],\\n        
\\"hash\\": v[6],\\n                    \\"timestamp\\": v[7],\\n               
\\"signature\\": v[8]\\n                }\\n                for v in votes\\n   
]\\n        }\\n        \\n        with open(output_path, \'w\') as f:\\n       
json.dump(export_data, f, indent=2)\\n        \\n        # Compute file hash\\n 
with open(output_path, \'rb\') as f:\\n            file_hash = 
hashlib.sha256(f.read()).hexdigest()\\n        \\n        # Record export\\n    
self.conn.execute(\\n            \\"\\"\\"INSERT INTO vote_audit_exports \\n    
(export_type, filename, file_hash, vote_start_id, vote_end_id, exported_by)\\n  
VALUES (?, ?, ?, ?, ?, ?)\\"\\"\\",\\n            (\\"json\\", output_path, 
file_hash, \\n             export_data[\\"export\\"][\\"start_id\\"],\\n        
export_data[\\"export\\"][\\"end_id\\"],\\n             \\"system\\")\\n        
)\\n        self.conn.commit()\\n        \\n        return {\\n            
\\"output_path\\": output_path,\\n            \\"file_hash\\": file_hash,\\n    
\\"merkle_root\\": root,\\n            \\"votes\\": len(votes)\\n        
}\\n```\\n\\n### 1.6 CLI Commands\\n\\n```bash\\n# Create a Merkle checkpoint 
for votes\\ncortex vote-ledger checkpoint\\n\\n# Verify vote ledger 
integrity\\ncortex vote-ledger verify\\n# Output: ✓ Chain valid (10,234 votes, 
10 Merkle roots)\\n#         ✓ All Merkle roots verified\\n#         ✓ No 
tampering detected\\n\\n# Export verifiable vote log\\ncortex vote-ledger export
--format json --output votes_2024.json\\n\\n# Get vote history for a 
fact\\ncortex vote-ledger history <fact_id>\\n\\n# Import and verify external 
vote log\\ncortex vote-ledger verify-external 
votes_2024.json\\n```\\n\\n---\\n\\n## 2. High-Availability Ledger 
Synchronization\\n\\n### 2.1 Problem Statement\\n\\nCurrent CORTEX operates as a
single-node system with no replication:\\n\\n```\\nCurrent 
State:\\n┌─────────────┐\\n│  CORTEX     │\\n│  (Single)   │\\n│  SQLite     
│\\n└─────────────┘\\n     │\\n     ▼\\n  [SPOF]  ← Single Point of 
Failure\\n```\\n\\n**Limitations:**\\n- ❌ No failover capability\\n- ❌ No 
geographic distribution\\n- ❌ Consensus votes lost if node fails\\n- ❌ No read
replicas for query scaling\\n\\n### 2.2 Design Goals\\n\\n| Goal | Priority | 
Description |\\n|------|----------|-------------|\\n| **Availability** | P0 | 
99.9% uptime with automatic failover |\\n| **Consistency** | P0 | Strong 
consistency for votes, eventual for reads |\\n| **Partition Tolerance** | P0 | 
Continue operating during network splits |\\n| **Conflict Resolution** | P1 | 
Automatic merge for concurrent writes |\\n| **Scalability** | P2 | Horizontal 
scaling for read-heavy workloads |\\n\\n### 2.3 Architecture: CRDT-Based 
Replication\\n\\n```\\n┌────────────────────────────────────────────────────────
─────────────────────┐\\n│                    HIGH-AVAILABILITY CORTEX CLUSTER  
│\\n├───────────────────────────────────────────────────────────────────────────
──┤\\n│                                                                         
     │\\n│   
┌───────────────────────────────────────────────────────────────────┐    │\\n│  
│                    CONSENSUS LAYER (Raft)                          │    │\\n│ 
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                           │    │\\n│   
│  │  Node 1 │  │  Node 2 │  │  Node 3 │  ← Leader Election         │    │\\n│  
│  │  Leader │◄─┤ Follower│◄─┤ Follower│                           │    │\\n│   
│  └────┬────┘  └────┬────┘  └────┬────┘                           │    │\\n│   
│       └─────────────┴─────────────┘                              │    │\\n│   
│                     │                                            │    │\\n│   
│                     ▼                                            │    │\\n│   
│         ┌─────────────────────┐                                  │    │\\n│   
│         │   Log Replication   │                                  │    │\\n│   
│         │   (Strong Consistency)│                                │    │\\n│   
│         └─────────────────────┘                                  │    │\\n│   
└───────────────────────────────────────────────────────────────────┘    │\\n│  
│                                         │\\n│                                 
▼                                         │\\n│   
┌───────────────────────────────────────────────────────────────────┐    │\\n│  
│                    DATA LAYER (CRDT)                               │    │\\n│ 
│                                                                    │    │\\n│ 
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │    │\\n│  
│  │   Node 1     │  │   Node 2     │  │   Node 3     │             │    │\\n│  
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │             │    │\\n│  
│  │ │  Facts   │ │  │ │  Facts   │ │  │ │  Facts   │ │             │    │\\n│  
│  │ │ (CRDT)   │◄┼──┼►│ (CRDT)   │◄┼──┼►│ (CRDT)   │ │             │    │\\n│  
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │             │    │\\n│  
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │             │    │\\n│  
│  │ │  Votes   │ │  │ │  Votes   │ │  │ │  Votes   │ │             │    │\\n│  
│  │ │ (CRDT)   │◄┼──┼►│ (CRDT)   │◄┼──┼►│ (CRDT)   │ │             │    │\\n│  
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │             │    │\\n│  
│  └──────────────┘  └──────────────┘  └──────────────┘             │    │\\n│  
│                                                                    │    │\\n│ 
│  Replication: Anti-entropy gossip (every 30s)                     │    │\\n│  
│  Conflict Resolution: LWW for facts, OR-Set for votes             │    │\\n│  
└───────────────────────────────────────────────────────────────────┘    │\\n│  
│\\n│   ┌───────────────────────────────────────────────────────────────────┐   
│\\n│   │                    SYNC PROTOCOL                                   │  
│\\n│   │                                                                    │  
│\\n│   │  1. Vector Clocks: Track causality across nodes                   │   
│\\n│   │  2. Merkle Trees: Efficient diff for synchronization              │   
│\\n│   │  3. Bloom Filters: Quick \\"has this changed?\\" checks               
│    │\\n│   │  4. Gossip Protocol: Epidemic broadcast for updates              
│    │\\n│   
└───────────────────────────────────────────────────────────────────┘    │\\n│  
│\\n└───────────────────────────────────────────────────────────────────────────
──┘\\n```\\n\\n### 2.4 Database Schema Extensions\\n\\n```sql\\n-- 
============================================================\\n-- MIGRATION 011:
High-Availability Synchronization\\n-- 
============================================================\\n\\n-- Node 
identity and cluster membership\\nCREATE TABLE cluster_nodes (\\n    node_id    
TEXT PRIMARY KEY,\\n    node_name       TEXT NOT NULL,\\n    node_address    
TEXT NOT NULL,          -- Host:port for communication\\n    node_region     
TEXT,                   -- Geographic region\\n    is_active       BOOLEAN 
DEFAULT TRUE,\\n    is_voter        BOOLEAN DEFAULT TRUE,   -- Participates in 
Raft consensus\\n    joined_at       TEXT NOT NULL DEFAULT 
(datetime(\'now\')),\\n    last_seen_at    TEXT NOT NULL DEFAULT 
(datetime(\'now\')),\\n    raft_role       TEXT,                   -- 
\'leader\', \'follower\', \'candidate\'\\n    meta            TEXT DEFAULT 
\'{}\'\\n);\\n\\n-- Vector clocks for causality tracking\\nCREATE TABLE 
vector_clocks (\\n    node_id         TEXT NOT NULL REFERENCES 
cluster_nodes(node_id),\\n    entity_type     TEXT NOT NULL,          -- 
\'fact\', \'vote\', \'agent\'\\n    entity_id       TEXT NOT NULL,          -- 
ID of the entity\\n    version         INTEGER NOT NULL DEFAULT 0,\\n    
timestamp       TEXT NOT NULL DEFAULT (datetime(\'now\')),\\n    PRIMARY KEY 
(node_id, entity_type, entity_id)\\n);\\n\\n-- Sync log for 
anti-entropy\\nCREATE TABLE sync_log (\\n    id              INTEGER PRIMARY KEY
AUTOINCREMENT,\\n    node_id         TEXT NOT NULL REFERENCES 
cluster_nodes(node_id),\\n    sync_type       TEXT NOT NULL,          -- 
\'push\', \'pull\', \'full\'\\n    entity_type     TEXT NOT NULL,\\n    
entity_count    INTEGER NOT NULL,\\n    started_at      TEXT NOT NULL,\\n    
completed_at    TEXT,\\n    status          TEXT,                   -- 
\'success\', \'failed\', \'partial\'\\n    details         TEXT                 
-- JSON with sync details\\n);\\n\\nCREATE INDEX idx_sync_log_node ON 
sync_log(node_id, completed_at);\\n\\n-- Conflict resolution log\\nCREATE TABLE 
conflict_log (\\n    id              INTEGER PRIMARY KEY AUTOINCREMENT,\\n    
entity_type     TEXT NOT NULL,\\n    entity_id       TEXT NOT NULL,\\n    
conflict_type   TEXT NOT NULL,          -- \'concurrent_update\', 
\'delete_update\'\\n    node_a          TEXT NOT NULL,\\n    node_b          
TEXT NOT NULL,\\n    resolution      TEXT NOT NULL,          -- \'lww\', 
\'merge\', \'manual\'\\n    resolved_at     TEXT NOT NULL DEFAULT 
(datetime(\'now\')),\\n    details         TEXT\\n);\\n\\n-- Merkle tree for 
efficient diff\\nCREATE TABLE sync_merkle (\\n    node_id         TEXT NOT 
NULL,\\n    entity_type     TEXT NOT NULL,\\n    bucket          INTEGER NOT 
NULL,       -- Hash bucket\\n    merkle_root     TEXT NOT NULL,\\n    updated_at
TEXT NOT NULL DEFAULT (datetime(\'now\')),\\n    PRIMARY KEY (node_id, 
entity_type, bucket)\\n);\\n```\\n\\n### 2.5 Implementation: HA 
Synchronization\\n\\n```python\\n# 
cortex/ha_sync.py\\n\\"\\"\\"\\nHigh-Availability Synchronization for 
CORTEX.\\n\\nFeatures:\\n- Raft consensus for leader election\\n- CRDT-based 
data replication\\n- Anti-entropy gossip protocol\\n- Automatic conflict 
resolution\\n\\"\\"\\"\\n\\nimport hashlib\\nimport json\\nimport 
sqlite3\\nimport asyncio\\nfrom typing import Dict, List, Optional, Set, 
Tuple\\nfrom dataclasses import dataclass, asdict\\nfrom datetime import 
datetime\\nfrom enum import Enum\\nimport random\\n\\n\\nclass 
NodeRole(Enum):\\n    LEADER = \\"leader\\"\\n    FOLLOWER = \\"follower\\"\\n  
CANDIDATE = \\"candidate\\"\\n\\n\\n@dataclass\\nclass VectorClock:\\n    
\\"\\"\\"Vector clock for causality tracking.\\"\\"\\"\\n    node_id: str\\n    
counters: Dict[str, int]\\n    \\n    def increment(self) -> 
\\"VectorClock\\":\\n        \\"\\"\\"Increment this node\'s 
counter.\\"\\"\\"\\n        new_counters = self.counters.copy()\\n        
new_counters[self.node_id] = new_counters.get(self.node_id, 0) + 1\\n        
return VectorClock(self.node_id, new_counters)\\n    \\n    def compare(self, 
other: \\"VectorClock\\") -> Optional[str]:\\n        \\"\\"\\"\\n        
Compare two vector clocks.\\n        Returns: \'before\', \'after\', 
\'concurrent\', or \'equal\'\\n        \\"\\"\\"\\n        all_nodes = 
set(self.counters.keys()) | set(other.counters.keys())\\n        \\n        
dominates = False\\n        dominated = False\\n        \\n        for node in 
all_nodes:\\n            a = self.counters.get(node, 0)\\n            b = 
other.counters.get(node, 0)\\n            \\n            if a > b:\\n           
dominates = True\\n            elif b > a:\\n                dominated = True\\n
\\n        if dominates and not dominated:\\n            return \\"after\\"\\n  
elif dominated and not dominates:\\n            return \\"before\\"\\n        
elif not dominates and not dominated:\\n            return \\"equal\\"\\n       
else:\\n            return \\"concurrent\\"\\n\\n\\n@dataclass\\nclass 
SyncState:\\n    \\"\\"\\"Current synchronization state.\\"\\"\\"\\n    node_id:
str\\n    role: NodeRole\\n    leader_id: Optional[str]\\n    term: int\\n    
last_heartbeat: datetime\\n    known_nodes: List[str]\\n\\n\\nclass 
HASyncManager:\\n    \\"\\"\\"\\n    Manages high-availability synchronization 
for CORTEX.\\n    \\n    Features:\\n    - Raft consensus for leader election\\n
- CRDT-based conflict-free replication\\n    - Anti-entropy gossip protocol\\n  
\\"\\"\\"\\n    \\n    def __init__(\\n        self,\\n        conn: 
sqlite3.Connection,\\n        node_id: str,\\n        node_address: str,\\n     
peers: List[str],\\n        gossip_interval: float = 30.0\\n    ):\\n        
self.conn = conn\\n        self.node_id = node_id\\n        self.node_address = 
node_address\\n        self.peers = peers\\n        self.gossip_interval = 
gossip_interval\\n        \\n        self.role = NodeRole.FOLLOWER\\n        
self.leader_id: Optional[str] = None\\n        self.term = 0\\n        
self.voted_for: Optional[str] = None\\n        \\n        self._running = 
False\\n        self._gossip_task: Optional[asyncio.Task] = None\\n    \\n    
def initialize_node(self) -> None:\\n        \\"\\"\\"Register this node in the 
cluster.\\"\\"\\"\\n        self.conn.execute(\\n            \\"\\"\\"\\n       
INSERT OR REPLACE INTO cluster_nodes \\n            (node_id, node_name, 
node_address, is_active, raft_role)\\n            VALUES (?, ?, ?, TRUE, ?)\\n  
\\"\\"\\",\\n            (self.node_id, self.node_id, self.node_address, 
self.role.value)\\n        )\\n        self.conn.commit()\\n    \\n    async def
start(self) -> None:\\n        \\"\\"\\"Start the HA sync manager.\\"\\"\\"\\n  
self._running = True\\n        self.initialize_node()\\n        \\n        # 
Start gossip protocol\\n        self._gossip_task = 
asyncio.create_task(self._gossip_loop())\\n        \\n        # Start Raft 
election timeout\\n        asyncio.create_task(self._raft_loop())\\n    \\n    
async def stop(self) -> None:\\n        \\"\\"\\"Stop the HA sync 
manager.\\"\\"\\"\\n        self._running = False\\n        if 
self._gossip_task:\\n            self._gossip_task.cancel()\\n    \\n    async 
def _gossip_loop(self) -> None:\\n        \\"\\"\\"Background task for 
anti-entropy gossip.\\"\\"\\"\\n        while self._running:\\n            
try:\\n                await self._perform_gossip()\\n            except 
Exception as e:\\n                print(f\\"Gossip error: {e}\\")\\n            
\\n            await asyncio.sleep(self.gossip_interval)\\n    \\n    async def 
_perform_gossip(self) -> None:\\n        \\"\\"\\"Perform anti-entropy with a 
random peer.\\"\\"\\"\\n        if not self.peers:\\n            return\\n      
\\n        # Select random peer\\n        peer = random.choice(self.peers)\\n   
\\n        # Get our Merkle roots\\n        our_roots = 
self._get_merkle_roots()\\n        \\n        # In real implementation, this 
would be an RPC call\\n        # For now, we simulate the sync process\\n       
peer_roots = await self._fetch_peer_roots(peer)\\n        \\n        # Find 
differences\\n        diffs = self._find_merkle_diffs(our_roots, peer_roots)\\n 
\\n        if diffs:\\n            # Sync missing data\\n            await 
self._sync_differences(peer, diffs)\\n    \\n    def _get_merkle_roots(self) -> 
Dict[str, Dict[int, str]]:\\n        \\"\\"\\"Get Merkle roots for all entity 
types.\\"\\"\\"\\n        cursor = self.conn.execute(\\n            \\"SELECT 
entity_type, bucket, merkle_root FROM sync_merkle WHERE node_id = ?\\",\\n      
(self.node_id,)\\n        )\\n        \\n        roots: Dict[str, Dict[int, 
str]] = {}\\n        for row in cursor.fetchall():\\n            entity_type, 
bucket, root = row\\n            if entity_type not in roots:\\n                
roots[entity_type] = {}\\n            roots[entity_type][bucket] = root\\n      
\\n        return roots\\n    \\n    async def _fetch_peer_roots(self, peer: 
str) -> Dict[str, Dict[int, str]]:\\n        \\"\\"\\"Fetch Merkle roots from a 
peer.\\"\\"\\"\\n        # In real implementation: RPC call to peer\\n        # 
Placeholder for demonstration\\n        return {}\\n    \\n    def 
_find_merkle_diffs(\\n        self,\\n        our_roots: Dict[str, Dict[int, 
str]],\\n        peer_roots: Dict[str, Dict[int, str]]\\n    ) -> 
List[Tuple[str, int]]:\\n        \\"\\"\\"Find buckets that differ between 
nodes.\\"\\"\\"\\n        diffs = []\\n        \\n        all_types = 
set(our_roots.keys()) | set(peer_roots.keys())\\n        \\n        for 
entity_type in all_types:\\n            our_buckets = our_roots.get(entity_type,
{})\\n            peer_buckets = peer_roots.get(entity_type, {})\\n            
\\n            all_buckets = set(our_buckets.keys()) | 
set(peer_buckets.keys())\\n            \\n            for bucket in 
all_buckets:\\n                our_root = our_buckets.get(bucket)\\n            
peer_root = peer_buckets.get(bucket)\\n                \\n                if 
our_root != peer_root:\\n                    diffs.append((entity_type, 
bucket))\\n        \\n        return diffs\\n    \\n    async def 
_sync_differences(\\n        self,\\n        peer: str,\\n        diffs: 
List[Tuple[str, int]]\\n    ) -> None:\\n        \\"\\"\\"Synchronize 
differences with a peer.\\"\\"\\"\\n        for entity_type, bucket in diffs:\\n
# In real implementation: fetch and merge entities\\n            pass\\n    \\n 
async def _raft_loop(self) -> None:\\n        \\"\\"\\"Raft consensus loop for 
leader election.\\"\\"\\"\\n        while self._running:\\n            timeout =
random.uniform(0.15, 0.3)  # 150-300ms election timeout\\n            \\n       
await asyncio.sleep(timeout)\\n            \\n            if self.role == 
NodeRole.FOLLOWER:\\n                # Check if we haven\'t heard from leader\\n
# Transition to candidate\\n                await self._start_election()\\n    
\\n    async def _start_election(self) -> None:\\n        \\"\\"\\"Start a Raft 
election.\\"\\"\\"\\n        self.term += 1\\n        self.role = 
NodeRole.CANDIDATE\\n        self.voted_for = self.node_id\\n        \\n        
# Request votes from peers\\n        votes = 1  # Vote for self\\n        \\n   
for peer in self.peers:\\n            # In real implementation: RPC call\\n     
# Placeholder\\n            pass\\n        \\n        # Check if we won\\n      
if votes > (len(self.peers) + 1) / 2:\\n            await 
self._become_leader()\\n    \\n    async def _become_leader(self) -> None:\\n   
\\"\\"\\"Transition to leader role.\\"\\"\\"\\n        self.role = 
NodeRole.LEADER\\n        self.leader_id = self.node_id\\n        \\n        
self.conn.execute(\\n            \\"UPDATE cluster_nodes SET raft_role = ? WHERE
node_id = ?\\",\\n            (NodeRole.LEADER.value, self.node_id)\\n        
)\\n        self.conn.commit()\\n        \\n        # Start sending 
heartbeats\\n        asyncio.create_task(self._send_heartbeats())\\n    \\n    
async def _send_heartbeats(self) -> None:\\n        \\"\\"\\"Send heartbeat 
messages to followers.\\"\\"\\"\\n        while self._running and self.role == 
NodeRole.LEADER:\\n            for peer in self.peers:\\n                # In 
real implementation: RPC call\\n                pass\\n            \\n          
await asyncio.sleep(0.05)  # 50ms heartbeat interval\\n    \\n    def 
replicate_vote(\\n        self,\\n        fact_id: int,\\n        agent_id: 
str,\\n        vote: int,\\n        vote_weight: float\\n    ) -> bool:\\n      
\\"\\"\\"\\n        Replicate a vote to the cluster.\\n        Only the leader 
can accept writes.\\n        \\"\\"\\"\\n        if self.role != 
NodeRole.LEADER:\\n            # Forward to leader\\n            return False\\n
\\n        # Append to local log\\n        # Replicate to followers\\n        # 
Wait for majority acknowledgment\\n        \\n        return True\\n    \\n    
def update_merkle_tree(self, entity_type: str, entity_id: str) -> None:\\n      
\\"\\"\\"Update Merkle tree after entity change.\\"\\"\\"\\n        # Compute 
bucket from entity_id hash\\n        bucket = 
int(hashlib.md5(entity_id.encode()).hexdigest(), 16) % 256\\n        \\n        
# Recompute Merkle root for this bucket\\n        # This is simplified - real 
implementation would recompute from entities\\n        new_root = 
hashlib.sha256(\\n            
f\\"{entity_type}:{entity_id}:{datetime.utcnow().isoformat()}\\".encode()\\n    
).hexdigest()\\n        \\n        self.conn.execute(\\n            \\"\\"\\"\\n
INSERT OR REPLACE INTO sync_merkle \\n            (node_id, entity_type, bucket,
merkle_root, updated_at)\\n            VALUES (?, ?, ?, ?, datetime(\'now\'))\\n
\\"\\"\\",\\n            (self.node_id, entity_type, bucket, new_root)\\n       
)\\n        self.conn.commit()\\n```\\n\\n---\\n\\n## 3. Edge Deployment via MCP
Server Optimization\\n\\n### 3.1 Problem Statement\\n\\nCurrent MCP server has 
limitations for edge deployment:\\n\\n| Aspect | Current | Edge Requirement 
|\\n|--------|---------|------------------|\\n| Transport | stdio only | 
Multiple transports (SSE, WebSocket, HTTP/2) |\\n| Concurrency | Blocking | 
Async with connection pooling |\\n| Caching | None | Multi-tier caching (LRU, 
distributed) |\\n| Batching | None | Multi-fact operations |\\n| Observability |
Basic logging | Metrics, traces, structured logs |\\n| Resource Usage | 
Unbounded | Memory/CPU limits for edge devices |\\n\\n### 3.2 Design 
Goals\\n\\n| Goal | Priority | Description 
|\\n|------|----------|-------------|\\n| **Low Latency** | P0 | <10ms p99 for 
cached queries |\\n| **High Throughput** | P0 | >1000 req/s per node |\\n| 
**Resource Efficiency** | P0 | <256MB RAM, <1 CPU core |\\n| **Transport 
Flexibility** | P1 | stdio, SSE, WebSocket, HTTP/2 |\\n| **Edge Caching** | P1 |
LRU + distributed cache support |\\n| **Observability** | P2 | Prometheus 
metrics, OpenTelemetry traces |\\n\\n### 3.3 Architecture: Optimized MCP 
Server\\n\\n```\\n┌─────────────────────────────────────────────────────────────
────────────────┐\\n│                    EDGE-OPTIMIZED MCP SERVER              
│\\n├───────────────────────────────────────────────────────────────────────────
──┤\\n│                                                                         
     │\\n│   
┌───────────────────────────────────────────────────────────────────┐    │\\n│  
│                      Transport Layer                               │    │\\n│ 
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐       │    │\\n│  
│  │  stdio   │  │   SSE    │  │  HTTP/2  │  │  WebSocket   │       │    │\\n│  
│  │(default) │  │ (server) │  │(streaming│  │ (real-time)  │       │    │\\n│  
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘       │    │\\n│  
│       └─────────────┴─────────────┴───────────────┘               │    │\\n│  
│                         │                                         │    │\\n│  
│                         ▼                                         │    │\\n│  
│              ┌─────────────────────┐                              │    │\\n│  
│              │   Protocol Handler  │                              │    │\\n│  
│              │   (MCP 2024-11-05)  │                              │    │\\n│  
│              └──────────┬──────────┘                              │    │\\n│  
└─────────────────────────┼─────────────────────────────────────────┘    │\\n│  
│                                               │\\n│   
┌─────────────────────────┼─────────────────────────────────────────┐    │\\n│  
│              ┌──────────▼──────────┐                               │    │\\n│ 
│              │    Request Router   │                               │    │\\n│ 
│              └──────────┬──────────┘                               │    │\\n│ 
│                         │                                          │    │\\n│ 
│   ┌─────────────────────┼─────────────────────┐                   │    │\\n│  
│   │                     │                     │                   │    │\\n│  
│   ▼                     ▼                     ▼                   │    │\\n│  
│ ┌──────────┐      ┌──────────┐      ┌──────────────────┐         │    │\\n│   
│ │  Tools   │      │Resources │      │  Prompt Templates │         │    │\\n│  
│ │ Registry │      │ Registry │      │    Registry      │         │    │\\n│   
│ └────┬─────┘      └────┬─────┘      └────────┬─────────┘         │    │\\n│   
│      │                 │                     │                   │    │\\n│   
└──────┼─────────────────┼─────────────────────┼───────────────────┘    │\\n│   
│                 │                     │                         │\\n│   
┌──────▼─────────────────▼─────────────────────▼────────────────────┐   │\\n│   
│                     Optimization Layer                             │   │\\n│  
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐     │   │\\n│   │
│  Multi-Tier  │  │   Request    │  │   Connection Pool   │     │   │\\n│   │  │
Cache     │  │   Batching   │  │    (SQLite WAL)     │     │   │\\n│   │  │ 
┌──────────┐ │  │              │  │                     │     │   │\\n│   │  │ │
L1:     │ │  │ ┌──────────┐ │  │ ┌─────────────────┐ │     │   │\\n│   │  │ │ 
In-Memory│ │  │ │  Batch   │ │  │ │  Async Pool     │ │     │   │\\n│   │  │ 
└──────────┘ │  │ │  Queue   │ │  │ │  (5 conns)      │ │     │   │\\n│   │  │ 
┌──────────┐ │  │ └──────────┘ │  │ └─────────────────┘ │     │   │\\n│   │  │ │
L2:     │ │  │              │  │                     │     │   │\\n│   │  │ │  
Redis   │ │  │ Flush: 10ms  │  │                     │     │   │\\n│   │  │ 
│(optional)│ │  │ Max: 100 ops │  │                     │     │   │\\n│   │  │ 
└──────────┘ │  │              │  │                     │     │   │\\n│   │  
└──────────────┘  └──────────────┘  └─────────────────────┘     │   │\\n│   │   
│   │\\n│   │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐     │
│\\n│   │  │   Circuit    │  │   Resource   │  │     Metrics         │     │   
│\\n│   │  │   Breaker    │  │    Limits    │  │   (Prometheus)      │     │   
│\\n│   │  │              │  │              │  │                     │     │   
│\\n│   │  │ Failure: 5   │  │ Memory: 256MB│  │ - Request latency   │     │   
│\\n│   │  │ Timeout: 30s │  │ CPU: 1 core  │  │ - Cache hit rate    │     │   
│\\n│   │  │ Cooldown: 5s │  │ Conns: 100   │  │ - Error rate        │     │   
│\\n│   │  └──────────────┘  └──────────────┘  └─────────────────────┘     │   
│\\n│   └────────────────────────────────────────────────────────────────────┘  
│\\n│                                                                           
│\\n│   ┌───────────────────────────────────────────────────────────────────┐   
│\\n│   │                      Engine Layer                                  │  
│\\n│   │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐     │    
│\\n│   │  │Query Cache   │  │ Write-Ahead  │  │   Embedding Cache   │     │    
│\\n│   │  │   (LRU)      │  │   Buffer     │  │    (LRU 100)        │     │    
│\\n│   │  └──────────────┘  └──────────────┘  └─────────────────────┘     │    
│\\n│   └───────────────────────────────────────────────────────────────────┘   
│\\n│                                                                           
│\\n└───────────────────────────────────────────────────────────────────────────
──┘\\n```\\n\\n### 3.4 Implementation: Edge-Optimized MCP 
Server\\n\\n```python\\n# cortex/mcp_server_edge.py\\n\\"\\"\\"\\nCORTEX MCP 
Server Edge — High-Performance Multi-Transport 
Implementation.\\n\\nFeatures:\\n- Async I/O with connection pooling\\n- 
Multiple transports (stdio, SSE, WebSocket, HTTP/2)\\n- Multi-tier caching (L1 
in-memory, L2 Redis)\\n- Request batching\\n- Circuit breaker pattern\\n- 
Resource limits\\n- Comprehensive metrics\\n\\"\\"\\"\\n\\nfrom __future__ 
import annotations\\n\\nimport asyncio\\nimport json\\nimport logging\\nimport 
time\\nimport resource\\nfrom contextlib import asynccontextmanager\\nfrom 
dataclasses import dataclass, field\\nfrom functools import lru_cache\\nfrom 
typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union\\nfrom 
enum import Enum\\n\\nimport sqlite3\\nfrom concurrent.futures import 
ThreadPoolExecutor\\n\\nlogger = 
logging.getLogger(\\"cortex.mcp.edge\\")\\n\\n\\n# 
─────────────────────────────────────────────────────────────────────────\\n# 
Configuration\\n# 
─────────────────────────────────────────────────────────────────────────\\n\\n@
dataclass\\nclass EdgeMCPConfig:\\n    \\"\\"\\"Configuration for edge-optimized
MCP server.\\"\\"\\"\\n    db_path: str = \\"~/.cortex/cortex.db\\"\\n    
max_workers: int = 4\\n    \\n    # Caching\\n    query_cache_size: int = 
1000\\n    embedding_cache_size: int = 100\\n    cache_ttl_seconds: float = 
300.0  # 5 minutes\\n    \\n    # Batching\\n    batch_size: int = 100\\n    
batch_flush_ms: float = 10.0\\n    \\n    # Resource limits\\n    max_memory_mb:
int = 256\\n    max_connections: int = 100\\n    \\n    # Circuit breaker\\n    
circuit_failure_threshold: int = 5\\n    circuit_timeout_seconds: float = 
30.0\\n    circuit_cooldown_seconds: float = 5.0\\n    \\n    # Metrics\\n    
enable_metrics: bool = True\\n    metrics_port: int = 9090\\n    \\n    # 
Transport\\n    transport: str = \\"stdio\\"  # \\"stdio\\", \\"sse\\", 
\\"websocket\\", \\"http2\\"\\n    host: str = \\"127.0.0.1\\"\\n    port: int =
9999\\n    keepalive_interval: float = 30.0\\n\\n\\n# 
─────────────────────────────────────────────────────────────────────────\\n# 
Circuit Breaker\\n# 
─────────────────────────────────────────────────────────────────────────\\n\\nc
lass CircuitState(Enum):\\n    CLOSED = \\"closed\\"       # Normal operation\\n
OPEN = \\"open\\"          # Failing, reject requests\\n    HALF_OPEN = 
\\"half_open\\"  # Testing if recovered\\n\\n\\nclass CircuitBreaker:\\n    
\\"\\"\\"Circuit breaker pattern for fault tolerance.\\"\\"\\"\\n    \\n    def 
__init__(\\n        self,\\n        failure_threshold: int = 5,\\n        
timeout_seconds: float = 30.0,\\n        cooldown_seconds: float = 5.0\\n    
):\\n        self.failure_threshold = failure_threshold\\n        
self.timeout_seconds = timeout_seconds\\n        self.cooldown_seconds = 
cooldown_seconds\\n        \\n        self.state = CircuitState.CLOSED\\n       
self.failures = 0\\n        self.last_failure_time: Optional[float] = None\\n   
self._lock = asyncio.Lock()\\n    \\n    async def call(self, func: Callable, 
*args, **kwargs) -> Any:\\n        \\"\\"\\"Execute function with circuit 
breaker protection.\\"\\"\\"\\n        async with self._lock:\\n            if 
self.state == CircuitState.OPEN:\\n                if time.time() - 
(self.last_failure_time or 0) > self.cooldown_seconds:\\n                    
self.state = CircuitState.HALF_OPEN\\n                else:\\n                  
raise Exception(\\"Circuit breaker is OPEN\\")\\n        \\n        try:\\n     
result = await asyncio.wait_for(\\n                func(*args, **kwargs),\\n    
timeout=self.timeout_seconds\\n            )\\n            \\n            async 
with self._lock:\\n                if self.state == CircuitState.HALF_OPEN:\\n  
self.state = CircuitState.CLOSED\\n                self.failures = 0\\n         
\\n            return result\\n            \\n        except Exception as e:\\n 
async with self._lock:\\n                self.failures += 1\\n                
self.last_failure_time = time.time()\\n                \\n                if 
self.failures >= self.failure_threshold:\\n                    self.state = 
CircuitState.OPEN\\n            \\n            raise\\n\\n\\n# 
─────────────────────────────────────────────────────────────────────────\\n# 
Multi-Tier Cache\\n# 
─────────────────────────────────────────────────────────────────────────\\n\\nc
lass MultiTierCache:\\n    \\"\\"\\"\\n    Multi-tier cache with L1 (in-memory) 
and L2 (Redis) layers.\\n    For edge deployment, L2 is optional.\\n    
\\"\\"\\"\\n    \\n    def __init__(\\n        self,\\n        l1_size: int = 
1000,\\n        ttl_seconds: float = 300.0,\\n        redis_url: Optional[str] =
None\\n    ):\\n        self.l1_size = l1_size\\n        self.ttl_seconds = 
ttl_seconds\\n        self._l1: Dict[str, tuple[Any, float]] = {}\\n        
self._lock = asyncio.Lock()\\n        \\n        # L2 cache (Redis) - optional 
for edge\\n        self._l2 = None\\n        if redis_url:\\n            try:\\n
import redis.asyncio as redis\\n                self._l2 = 
redis.from_url(redis_url)\\n            except ImportError:\\n                
logger.warning(\\"Redis not available, using L1 cache only\\")\\n    \\n    def 
_key(self, prefix: str, **params) -> str:\\n        \\"\\"\\"Generate cache key 
from parameters.\\"\\"\\"\\n        sorted_params = sorted(params.items())\\n   
param_str = json.dumps(sorted_params, sort_keys=True)\\n        return 
f\\"{prefix}:{hashlib.md5(param_str.encode()).hexdigest()}\\"\\n    \\n    async
def get(self, key: str) -> Optional[Any]:\\n        \\"\\"\\"Get value from 
cache.\\"\\"\\"\\n        now = time.time()\\n        \\n        # Check L1\\n  
async with self._lock:\\n            if key in self._l1:\\n                
value, expiry = self._l1[key]\\n                if expiry > now:\\n             
return value\\n                else:\\n                    del self._l1[key]\\n 
\\n        # Check L2 (if available)\\n        if self._l2:\\n            
try:\\n                value = await self._l2.get(key)\\n                if 
value:\\n                    data = json.loads(value)\\n                    # 
Promote to L1\\n                    async with self._lock:\\n                   
self._l1[key] = (data, now + self.ttl_seconds)\\n                    return 
data\\n            except Exception as e:\\n                logger.warning(\\"L2
cache error: %s\\", e)\\n        \\n        return None\\n    \\n    async def 
set(self, key: str, value: Any) -> None:\\n        \\"\\"\\"Set value in 
cache.\\"\\"\\"\\n        now = time.time()\\n        expiry = now + 
self.ttl_seconds\\n        \\n        # Set L1\\n        async with 
self._lock:\\n            # Evict oldest if at capacity\\n            while 
len(self._l1) >= self.l1_size:\\n                oldest_key = 
min(self._l1.keys(), key=lambda k: self._l1[k][1])\\n                del 
self._l1[oldest_key]\\n            \\n            self._l1[key] = (value, 
expiry)\\n        \\n        # Set L2 (if available)\\n        if self._l2:\\n  
try:\\n                await self._l2.setex(\\n                    key,\\n      
int(self.ttl_seconds),\\n                    json.dumps(value)\\n               
)\\n            except Exception as e:\\n                logger.warning(\\"L2 
cache error: %s\\", e)\\n    \\n    async def invalidate(self, pattern: str) -> 
None:\\n        \\"\\"\\"Invalidate cache entries matching pattern.\\"\\"\\"\\n 
async with self._lock:\\n            keys_to_remove = [k for k in 
self._l1.keys() if pattern in k]\\n            for k in keys_to_remove:\\n      
del self._l1[k]\\n        \\n        if self._l2:\\n            try:\\n         
# Note: This is inefficient, production would use Redis SCAN\\n                
pass\\n            except Exception as e:\\n                logger.warning(\\"L2
cache error: %s\\", e)\\n\\n\\n# 
─────────────────────────────────────────────────────────────────────────\\n# 
Request Batcher\\n# 
─────────────────────────────────────────────────────────────────────────\\n\\n@
dataclass\\nclass BatchItem:\\n    \\"\\"\\"Single item in a batch.\\"\\"\\"\\n 
request: dict\\n    future: asyncio.Future\\n\\n\\nclass RequestBatcher:\\n    
\\"\\"\\"Batches multiple requests for efficient processing.\\"\\"\\"\\n    \\n 
def __init__(self, max_size: int = 100, flush_ms: float = 10.0):\\n        
self.max_size = max_size\\n        self.flush_ms = flush_ms\\n        
self._batch: List[BatchItem] = []\\n        self._lock = asyncio.Lock()\\n      
self._flush_task: Optional[asyncio.Task] = None\\n    \\n    async def add(self,
request: dict) -> asyncio.Future:\\n        \\"\\"\\"Add a request to the 
batch.\\"\\"\\"\\n        future = asyncio.get_event_loop().create_future()\\n  
item = BatchItem(request, future)\\n        \\n        async with self._lock:\\n
self._batch.append(item)\\n            \\n            if len(self._batch) >= 
self.max_size:\\n                await self._flush()\\n            elif 
self._flush_task is None:\\n                self._flush_task = 
asyncio.create_task(self._delayed_flush())\\n        \\n        return future\\n
\\n    async def _delayed_flush(self) -> None:\\n        \\"\\"\\"Flush batch 
after delay.\\"\\"\\"\\n        await asyncio.sleep(self.flush_ms / 1000)\\n    
async with self._lock:\\n            await self._flush()\\n            
self._flush_task = None\\n    \\n    async def _flush(self) -> None:\\n        
\\"\\"\\"Process all batched requests.\\"\\"\\"\\n        if not self._batch:\\n
return\\n        \\n        batch = self._batch[:]\\n        self._batch = []\\n
\\n        # Process batch\\n        # In real implementation, this would 
execute batch query\\n        for item in batch:\\n            try:\\n          
result = await self._process_single(item.request)\\n                
item.future.set_result(result)\\n            except Exception as e:\\n          
item.future.set_exception(e)\\n    \\n    async def _process_single(self, 
request: dict) -> dict:\\n        \\"\\"\\"Process a single request.\\"\\"\\"\\n
# Placeholder - real implementation would batch SQL operations\\n        return 
{\\"status\\": \\"ok\\"}\\n\\n\\n# 
─────────────────────────────────────────────────────────────────────────\\n# 
Resource Monitor\\n# 
─────────────────────────────────────────────────────────────────────────\\n\\nc
lass ResourceMonitor:\\n    \\"\\"\\"Monitor and enforce resource 
limits.\\"\\"\\"\\n    \\n    def __init__(self, max_memory_mb: int = 256, 
max_connections: int = 100):\\n        self.max_memory_mb = max_memory_mb\\n    
self.max_connections = max_connections\\n        self.active_connections = 0\\n 
self._lock = asyncio.Lock()\\n    \\n    def check_memory(self) -> bool:\\n     
\\"\\"\\"Check if memory usage is within limits.\\"\\"\\"\\n        try:\\n     
import psutil\\n            process = psutil.Process()\\n            memory_mb =
process.memory_info().rss / 1024 / 1024\\n            return memory_mb < 
self.max_memory_mb\\n        except ImportError:\\n            # Fallback: use 
resource module\\n            import resource\\n            usage = 
resource.getrusage(resource.RUSAGE_SELF)\\n            memory_mb = 
usage.ru_maxrss / 1024  # KB to MB\\n            return memory_mb < 
self.max_memory_mb\\n    \\n    @asynccontextmanager\\n    async def 
acquire_connection(self):\\n        \\"\\"\\"Acquire a connection 
slot.\\"\\"\\"\\n        async with self._lock:\\n            if 
self.active_connections >= self.max_connections:\\n                raise 
Exception(\\"Max connections exceeded\\")\\n            self.active_connections 
+= 1\\n        \\n        try:\\n            yield\\n        finally:\\n        
async with self._lock:\\n                self.active_connections -= 1\\n    \\n 
def get_stats(self) -> dict:\\n        \\"\\"\\"Get resource 
statistics.\\"\\"\\"\\n        try:\\n            import psutil\\n            
process = psutil.Process()\\n            memory_mb = process.memory_info().rss /
1024 / 1024\\n            cpu_percent = process.cpu_percent()\\n        except 
ImportError:\\n            memory_mb = 0\\n            cpu_percent = 0\\n       
\\n        return {\\n            \\"memory_mb\\": memory_mb,\\n            
\\"memory_limit_mb\\": self.max_memory_mb,\\n            
\\"active_connections\\": self.active_connections,\\n            
\\"max_connections\\": self.max_connections,\\n            \\"cpu_percent\\": 
cpu_percent\\n        }\\n\\n\\n# 
─────────────────────────────────────────────────────────────────────────\\n# 
Edge-Optimized MCP Server\\n# 
─────────────────────────────────────────────────────────────────────────\\n\\nc
lass EdgeMCPServer:\\n    \\"\\"\\"\\n    Edge-optimized MCP server for 
CORTEX.\\n    \\n    Features:\\n    - Multi-tier caching\\n    - Request 
batching\\n    - Circuit breaker\\n    - Resource monitoring\\n    - Multiple 
transports\\n    \\"\\"\\"\\n    \\n    def __init__(self, config: 
Optional[EdgeMCPConfig] = None):\\n        self.config = config or 
EdgeMCPConfig()\\n        self.metrics = MCPMetrics()\\n        self.pool: 
Optional[AsyncConnectionPool] = None\\n        self.executor = 
ThreadPoolExecutor(max_workers=self.config.max_workers)\\n        \\n        # 
Components\\n        self.cache = MultiTierCache(\\n            
l1_size=self.config.query_cache_size,\\n            
ttl_seconds=self.config.cache_ttl_seconds\\n        )\\n        self.batcher = 
RequestBatcher(\\n            max_size=self.config.batch_size,\\n            
flush_ms=self.config.batch_flush_ms\\n        )\\n        self.circuit = 
CircuitBreaker(\\n            
failure_threshold=self.config.circuit_failure_threshold,\\n            
timeout_seconds=self.config.circuit_timeout_seconds,\\n            
cooldown_seconds=self.config.circuit_cooldown_seconds\\n        )\\n        
self.resources = ResourceMonitor(\\n            
max_memory_mb=self.config.max_memory_mb,\\n            
max_connections=self.config.max_connections\\n        )\\n        \\n        # 
Running flag\\n        self._running = False\\n    \\n    async def 
initialize(self):\\n        \\"\\"\\"Initialize the server.\\"\\"\\"\\n        #
Initialize connection pool\\n        db_path = 
os.path.expanduser(self.config.db_path)\\n        self.pool = 
AsyncConnectionPool(db_path, max_connections=self.config.max_workers)\\n        
await self.pool.initialize()\\n        \\n        # Initialize database\\n      
from cortex.migrations import run_migrations\\n        async with 
self.pool.acquire() as conn:\\n            loop = asyncio.get_event_loop()\\n   
await loop.run_in_executor(self.executor, run_migrations, conn)\\n        \\n   
self._running = True\\n        logger.info(\\"Edge MCP server initialized\\")\\n
\\n    async def cortex_store(\\n        self,\\n        project: str,\\n       
content: str,\\n        fact_type: str = \\"knowledge\\",\\n        tags: str = 
\\"[]\\",\\n        source: str = \\"\\",\\n        batch: bool = False\\n    ) 
-> dict:\\n        \\"\\"\\"\\n        Store a fact (or batch of facts) in 
CORTEX with optimizations.\\n        \\"\\"\\"\\n        from cortex.engine 
import CortexEngine\\n        \\n        start = time.time()\\n        \\n      
async with self.pool.acquire() as conn:\\n            engine = 
CortexEngine(self.config.db_path, auto_embed=False)\\n            engine._conn =
conn\\n            \\n            try:\\n                if batch:\\n           
facts = json.loads(content)\\n                    loop = 
asyncio.get_event_loop()\\n                    ids = await 
loop.run_in_executor(\\n                        self.executor,\\n               
engine.store_many,\\n                        facts\\n                    )\\n   
result = {\\n                        \\"success\\": True,\\n                    
\\"fact_ids\\": ids,\\n                        \\"count\\": len(ids)\\n         
}\\n                else:\\n                    parsed_tags = json.loads(tags) 
if tags else []\\n                    loop = asyncio.get_event_loop()\\n        
fact_id = await loop.run_in_executor(\\n                        
self.executor,\\n                        engine.store,\\n                       
project,\\n                        content,\\n                        
fact_type,\\n                        parsed_tags,\\n                        
\\"stated\\",\\n                        source or None,\\n                      
None,\\n                        None\\n                    )\\n                 
result = {\\n                        \\"success\\": True,\\n                    
\\"fact_id\\": fact_id\\n                    }\\n                \\n            
# Invalidate cache\\n                await 
self.cache.invalidate(f\\"search:{project}\\")\\n                await 
self.cache.invalidate(f\\"recall:{project}\\")\\n                \\n            
duration_ms = (time.time() - start) * 1000\\n                
self.metrics.record_request(\\"cortex_store\\", duration_ms)\\n                
\\n                return result\\n                \\n            except 
Exception as e:\\n                self.metrics.record_error()\\n                
logger.error(\\"Error in cortex_store: %s\\", e)\\n                raise\\n    
\\n    async def cortex_search(\\n        self,\\n        query: str,\\n        
project: str = \\"\\",\\n        top_k: int = 5,\\n        as_of: str = 
\\"\\",\\n        use_cache: bool = True\\n    ) -> dict:\\n        
\\"\\"\\"Search CORTEX with multi-tier caching.\\"\\"\\"\\n        from 
cortex.engine import CortexEngine\\n        \\n        cache_key = 
self.cache._key(\\n            \\"search\\",\\n            query=query,\\n      
project=project,\\n            top_k=top_k,\\n            as_of=as_of\\n        
)\\n        \\n        # Check cache\\n        if use_cache:\\n            
cached = await self.cache.get(cache_key)\\n            if cached is not None:\\n
self.metrics.record_request(\\"cortex_search\\", 0, cached=True)\\n             
return cached\\n        \\n        # Execute search\\n        start = 
time.time()\\n        \\n        async def _do_search():\\n            async 
with self.pool.acquire() as conn:\\n                engine = 
CortexEngine(self.config.db_path, auto_embed=False)\\n                
engine._conn = conn\\n                \\n                loop = 
asyncio.get_event_loop()\\n                results = await 
loop.run_in_executor(\\n                    self.executor,\\n                   
engine.search,\\n                    query,\\n                    project or 
None,\\n                    top_k,\\n                    as_of or None\\n       
)\\n                \\n                return [\\n                    {\\n      
\\"fact_id\\": r.fact_id,\\n                        \\"project\\": r.project,\\n
\\"content\\": r.content[:200] + \\"...\\" if len(r.content) > 200 else 
r.content,\\n                        \\"score\\": r.score,\\n                   
\\"consensus_score\\": getattr(r, \'consensus_score\', 1.0)\\n                  
}\\n                    for r in results\\n                ]\\n        \\n      
# Use circuit breaker\\n        results = await self.circuit.call(_do_search)\\n
\\n        result = {\\n            \\"results\\": results,\\n            
\\"count\\": len(results),\\n            \\"query\\": query\\n        }\\n      
\\n        # Cache result\\n        if use_cache:\\n            await 
self.cache.set(cache_key, result)\\n        \\n        duration_ms = 
(time.time() - start) * 1000\\n        
self.metrics.record_request(\\"cortex_search\\", duration_ms)\\n        \\n     
return result\\n    \\n    async def get_metrics(self) -> dict:\\n        
\\"\\"\\"Return server metrics.\\"\\"\\"\\n        return {\\n            
**self.metrics.get_summary(),\\n            **self.resources.get_stats()\\n     
}\\n    \\n    async def health_check(self) -> dict:\\n        \\"\\"\\"Health 
check endpoint.\\"\\"\\"\\n        healthy = self.resources.check_memory()\\n   
\\n        try:\\n            async with self.pool.acquire() as conn:\\n        
conn.execute(\\"SELECT 1\\")\\n            db_status = \\"connected\\"\\n       
except Exception as e:\\n            db_status = f\\"error: {e}\\"\\n        \\n
return {\\n            \\"status\\": \\"healthy\\" if healthy else 
\\"unhealthy\\",\\n            \\"database\\": db_status,\\n            
\\"circuit_state\\": self.circuit.state.value,\\n            \\"resources\\": 
self.resources.get_stats()\\n        }\\n    \\n    async def close(self):\\n   
\\"\\"\\"Shutdown the server.\\"\\"\\"\\n        self._running = False\\n       
if self.pool:\\n            await self.pool.close()\\n        
self.executor.shutdown(wait=True)\\n\\n\\n# Entry point\\nif __name__ == 
\\"__main__\\":\\n    import sys\\n    \\n    config = EdgeMCPConfig(\\n        
db_path=os.environ.get(\\"CORTEX_DB\\", \\"~/.cortex/cortex.db\\"),\\n        
transport=\\"stdio\\"\\n    )\\n    \\n    server = EdgeMCPServer(config)\\n    
asyncio.run(server.initialize())\\n```\\n\\n### 3.5 Performance Targets\\n\\n| 
Metric | Current | Target | Speedup 
|\\n|--------|---------|--------|---------|\\n| Cold search | 50ms | 50ms | — 
|\\n| Warm search | 50ms | 1ms | **50x** |\\n| Batch store (100) | 2300ms | 
450ms | **5x** |\\n| Throughput | 100 req/s | 1000 req/s | **10x** |\\n| Memory 
usage | Unbounded | <256MB | **Bounded** |\\n| P99 latency | Variable | <10ms | 
**Consistent** |\\n\\n---\\n\\n## 4. Deployment Patterns\\n\\n### 4.1 Docker 
Deployment\\n\\n```dockerfile\\n# Dockerfile.edge\\nFROM python:3.12-slim\\n\\n#
Install system dependencies\\nRUN apt-get update && apt-get install -y \\\\\\n  
libsqlite3-dev \\\\\\n    && rm -rf /var/lib/apt/lists/*\\n\\n# Set working 
directory\\nWORKDIR /app\\n\\n# Install Python dependencies\\nCOPY 
pyproject.toml .\\nRUN pip install --no-cache-dir -e \\".[edge]\\"\\n\\n# Copy 
application\\nCOPY cortex/ ./cortex/\\n\\n# Create non-root user\\nRUN useradd 
-m -u 1000 cortex && \\\\\\n    mkdir -p /data && \\\\\\n    chown -R 
cortex:cortex /data\\n\\n# Environment\\nENV CORTEX_DB=/data/cortex.db\\nENV 
CORTEX_MAX_MEMORY_MB=256\\nENV PYTHONUNBUFFERED=1\\n\\nUSER cortex\\n\\n# Expose
ports\\nEXPOSE 8484 9999\\n\\n# Health check\\nHEALTHCHECK --interval=30s 
--timeout=5s --start-period=5s --retries=3 \\\\\\n    CMD python -c \\"import 
requests; requests.get(\'http://localhost:8484/health\')\\" || exit 1\\n\\n# 
Default: run edge-optimized MCP server\\nCMD [\\"python\\", \\"-m\\", 
\\"cortex.mcp_server_edge\\"]\\n```\\n\\n### 4.2 Kubernetes 
Deployment\\n\\n```yaml\\n# deploy/k8s-edge-deployment.yaml\\napiVersion: 
apps/v1\\nkind: Deployment\\nmetadata:\\n  name: cortex-edge\\n  labels:\\n    
app: cortex-edge\\nspec:\\n  replicas: 3\\n  selector:\\n    matchLabels:\\n    
app: cortex-edge\\n  template:\\n    metadata:\\n      labels:\\n        app: 
cortex-edge\\n    spec:\\n      containers:\\n      - name: cortex\\n        
image: cortex:v5.0.0-edge\\n        ports:\\n        - containerPort: 8484\\n   
name: api\\n        - containerPort: 9999\\n          name: mcp\\n        
env:\\n        - name: CORTEX_DB\\n          value: \\"/data/cortex.db\\"\\n    
- name: CORTEX_MAX_MEMORY_MB\\n          value: \\"256\\"\\n        - name: 
CORTEX_CACHE_TTL\\n          value: \\"300\\"\\n        resources:\\n          
limits:\\n            memory: \\"256Mi\\"\\n            cpu: \\"1000m\\"\\n     
requests:\\n            memory: \\"128Mi\\"\\n            cpu: \\"250m\\"\\n    
volumeMounts:\\n        - name: data\\n          mountPath: /data\\n        
livenessProbe:\\n          httpGet:\\n            path: /health\\n            
port: 8484\\n          initialDelaySeconds: 10\\n          periodSeconds: 30\\n 
readinessProbe:\\n          httpGet:\\n            path: /health\\n            
port: 8484\\n          initialDelaySeconds: 5\\n          periodSeconds: 5\\n   
volumes:\\n      - name: data\\n        emptyDir: {}\\n---\\napiVersion: 
v1\\nkind: Service\\nmetadata:\\n  name: cortex-edge\\nspec:\\n  selector:\\n   
app: cortex-edge\\n  ports:\\n  - port: 8484\\n    targetPort: 8484\\n    name: 
api\\n  - port: 9999\\n    targetPort: 9999\\n    name: mcp\\n  type: 
ClusterIP\\n```\\n\\n### 4.3 Edge Device Deployment (IoT/ARM)\\n\\n```yaml\\n# 
docker-compose.edge.yml\\nversion: \\"3.8\\"\\n\\nservices:\\n  cortex-edge:\\n 
build:\\n      context: .\\n      dockerfile: Dockerfile.edge\\n      
platforms:\\n        - linux/arm64\\n        - linux/arm/v7\\n    ports:\\n     
- \\"8484:8484\\"\\n      - \\"9999:9999\\"\\n    volumes:\\n      - 
./data:/data\\n    environment:\\n      - CORTEX_DB=/data/cortex.db\\n      - 
CORTEX_MAX_MEMORY_MB=128\\n      - CORTEX_QUERY_CACHE_SIZE=500\\n      - 
CORTEX_BATCH_SIZE=50\\n    restart: unless-stopped\\n    deploy:\\n      
resources:\\n        limits:\\n          memory: 128M\\n          cpus: 
\'0.5\'\\n```\\n\\n---\\n\\n## 5. Migration Plan\\n\\n### 5.1 Wave 5 
Timeline\\n\\n```\\nWeek 1-2: Immutable Vote Ledger\\n├── Migration 010: Vote 
ledger schema\\n├── Implementation: VoteLedger class\\n├── Integration: Hook 
into vote() method\\n├── CLI: vote-ledger commands\\n└── Tests: 95% 
coverage\\n\\nWeek 3-4: HA Synchronization\\n├── Migration 011: HA schema 
(nodes, vector clocks, sync log)\\n├── Implementation: HASyncManager class\\n├──
Implementation: Raft consensus\\n├── Implementation: CRDT merge strategies\\n└──
Tests: Multi-node simulation\\n\\nWeek 5-6: Edge MCP Optimization\\n├── 
mcp_server_edge.py implementation\\n├── Multi-tier caching\\n├── Request 
batching\\n├── Circuit breaker\\n├── Resource monitoring\\n└── Benchmark 
suite\\n\\nWeek 7: Deployment\\n├── Dockerfile.edge\\n├── 
docker-compose.edge.yml\\n├── Kubernetes manifests\\n├── ARM/IoT builds\\n└── 
Documentation\\n\\nWeek 8: Integration & Testing\\n├── End-to-end HA tests\\n├──
Performance validation\\n├── Edge deployment tests\\n├── Security audit\\n└── 
Release candidate\\n```\\n\\n### 5.2 Migration Commands\\n\\n```bash\\n# Upgrade
to Wave 5\\ncortex migrate\\n\\n# Initialize vote ledger\\ncortex vote-ledger 
init\\n\\n# Create first Merkle checkpoint\\ncortex vote-ledger 
checkpoint\\n\\n# Verify integrity\\ncortex vote-ledger verify\\n\\n# Join HA 
cluster\\ncortex cluster join --node-id node2 --peers node1:8484\\n\\n# Start 
edge-optimized MCP server\\ncortex mcp start --transport sse --port 9999 
--edge-mode\\n\\n# Run benchmarks\\ncortex benchmark --suite 
edge\\n```\\n\\n---\\n\\n## 6. Success Criteria\\n\\n### 6.1 Technical 
Metrics\\n\\n| Metric | Target | Measurement 
|\\n|--------|--------|-------------|\\n| Vote Ledger Verification | <100ms for 
10k votes | `cortex vote-ledger verify` |\\n| HA Failover Time | <5 seconds | 
Simulated node failure |\\n| Data Consistency | 100% | Multi-node write/read 
test |\\n| MCP Cold Query | <50ms | Benchmark suite |\\n| MCP Warm Query | <1ms 
| Benchmark suite |\\n| MCP Throughput | >1000 req/s | Load test |\\n| Cache Hit
Rate | >80% | Runtime metrics |\\n| Memory Usage | <256MB | Container metrics 
|\\n| Edge Boot Time | <3 seconds | Cold start measurement |\\n\\n### 6.2 
Adoption Metrics\\n\\n| Metric | Target |\\n|--------|--------|\\n| API uptime |
99.9% |\\n| Error rate | <0.1% |\\n| Mean recovery time | <5 minutes |\\n| Vote 
tamper detection | 100% |\\n| Consensus consistency | 99.99% |\\n\\n---\\n\\n## 
7. Security Considerations\\n\\n### 7.1 Threat Model\\n\\n| Threat | Mitigation 
|\\n|--------|------------|\\n| Vote tampering | Immutable ledger with Merkle 
trees |\\n| Node compromise | Raft consensus requires majority |\\n| Network 
partition | CRDT merge strategies |\\n| Replay attacks | Vector clocks + 
timestamps |\\n| Sybil attacks | Reputation-weighted consensus (Wave 4) |\\n| 
DoS | Circuit breaker + rate limiting |\\n\\n### 7.2 Audit Requirements\\n\\n- 
All votes cryptographically chained\\n- Merkle roots for batch verification\\n- 
Exportable audit logs\\n- External anchoring support (optional)\\n- Tamper 
detection alerts\\n\\n---\\n\\n## Appendix A: API Changes\\n\\n### New 
Endpoints\\n\\n```\\nPOST   /v1/vote-ledger/checkpoint      # Create Merkle 
checkpoint\\nGET    /v1/vote-ledger/verify          # Verify vote ledger 
integrity\\nPOST   /v1/vote-ledger/export          # Export verifiable vote 
log\\nGET    /v1/vote-ledger/history/{fact_id} # Get vote history for 
fact\\n\\nPOST   /v1/cluster/join                # Join HA cluster\\nPOST   
/v1/cluster/leave               # Leave HA cluster\\nGET    /v1/cluster/status  
# Get cluster status\\nGET    /v1/cluster/nodes               # List cluster 
nodes\\n\\nGET    /v1/edge/metrics                # Edge server metrics\\nGET   
/v1/edge/health                 # Edge health check\\nPOST   
/v1/edge/cache/invalidate       # Invalidate cache\\n```\\n\\n### New CLI 
Commands\\n\\n```\\ncortex vote-ledger checkpoint          # Create 
checkpoint\\ncortex vote-ledger verify              # Verify integrity\\ncortex 
vote-ledger export              # Export log\\ncortex vote-ledger history 
<fact_id>   # Get vote history\\n\\ncortex cluster join                    # 
Join cluster\\ncortex cluster leave                   # Leave cluster\\ncortex 
cluster status                  # Show cluster status\\ncortex cluster nodes    
# List nodes\\n\\ncortex mcp start --edge-mode           # Start edge MCP 
server\\ncortex benchmark --suite edge          # Run edge 
benchmarks\\n```\\n\\n---\\n\\n**End of Wave 5 Proposal**\\n\\n*Prepared for 
CORTEX V4.0 Architecture Review | 2026-02-16*\\n"}'
    ),
    extras=None
)
StatusUpdate(
    context_usage=0.20935440063476562,
    token_usage=TokenUsage(
        input_other=353,
        output=18485,
        input_cache_read=54528,
        input_cache_creation=0
    ),
    message_id='chatcmpl-lCuvu7evV8rl6mYwVIMQ4B3u'
)
ToolResult(
    tool_call_id='tool_QoKduwydVKveVVrBw2bLTOS0',
    return_value=ToolReturnValue(
        is_error=False,
        output='',
        message='File successfully overwritten. Current size: 82277 bytes.',
        display=[
            DiffDisplayBlock(
                type='diff',
                path='/Users/borjafernandezangulo/cortex/WAVE5_PROPOSAL_PERSISTE
NCE_DEPLOYMENT.md',
                old_text='',
                new_text='# CORTEX V4.0 — Wave 5: Persistence & Deployment\n## 
Production-Ready Consensus Infrastructure\n\n**Date:** 2026-02-16  
\n**Version:** 5.0.0-proposal  \n**Status:** Technical Design Document  
\n**Author:** CORTEX Architecture Team  \n\n---\n\n## Executive Summary\n\nWave 
5 transforms CORTEX from a development-ready system into a **production-grade 
sovereign memory infrastructure**. Building upon the Reputation-Weighted 
Consensus (RWC) foundation from Wave 4, this wave delivers three critical 
capabilities:\n\n1. **Immutable Vote Logging** — Cryptographically 
tamper-evident consensus audit trail\n2. **High-Availability Ledger 
Synchronization** — Multi-node consensus with conflict-free replication\n3. 
**Edge-Optimized MCP Server** — High-performance Model Context Protocol for 
distributed deployments\n\n### Wave Completion Status\n\n| Wave | Feature | 
Status |\n|------|---------|--------|\n| Wave 1 | Core Engine (Facts, Search, 
Embeddings) | ✅ Complete |\n| Wave 2 | Temporal Facts & Transaction Ledger | ✅
Complete |\n| Wave 3 | REST API, Auth, Dashboard | ✅ Complete |\n| Wave 4 | 
Consensus Layer (RWC) | ✅ Complete |\n| **Wave 5** | **Persistence & 
Deployment** | 🔄 **Proposed** |\n| Wave 6 | Swarm Federation & Bridge Protocols
| 📋 Planned |\n\n---\n\n## 1. Immutable Vote Logging\n\n### 1.1 Problem 
Statement\n\nThe current consensus system has critical audit 
gaps:\n\n```python\n# Current Implementation (Wave 4)\n# Votes are stored but 
NOT linked to the immutable ledger\nconn.execute(\n    "INSERT INTO 
consensus_votes_v2 (fact_id, agent_id, vote, vote_weight) ..."\n)\n# No 
cryptographic proof of vote existence\n# No protection against "God Key" 
database admin attacks\n# No external 
verifiability\n```\n\n**Vulnerabilities:**\n- ❌ Votes can be modified by 
database administrators\n- ❌ No cryptographic proof of vote ordering/timing\n- 
❌ No mechanism for external audit\n- ❌ Vote history can be selectively 
deleted\n\n### 1.2 Design Goals\n\n| Goal | Priority | Description 
|\n|------|----------|-------------|\n| **Tamper-Proof** | P0 | Cryptographic 
guarantees against any modification |\n| **Verifiable** | P0 | Third parties can
verify integrity without trust |\n| **Ordered** | P0 | Strict temporal ordering 
of all votes |\n| **Efficient** | P1 | <5ms overhead per vote |\n| 
**Exportable** | P1 | JSON/CSV export for external auditors |\n| **Redundant** |
P2 | Multiple storage backends (local + remote hash log) |\n\n### 1.3 
Architecture: Hierarchical Vote 
Ledger\n\n```\n┌────────────────────────────────────────────────────────────────
─────────────┐\n│                    IMMUTABLE VOTE LEDGER ARCHITECTURE         
│\n├────────────────────────────────────────────────────────────────────────────
─┤\n│                                                                           
   │\n│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐            
│\n│   │  Vote Cast   │────▶│  Vote Entry  │────▶│  Hash Chain  │               
│\n│   │   (Event)    │     │  (SQLite)    │     │  (SHA-256)   │               
│\n│   └──────────────┘     └──────────────┘     └──────┬───────┘               
│\n│                                                     │                      
│\n│                              ┌──────────────────────┘                      
│\n│                              ▼                                             
│\n│   ┌────────────────────────────────────────────────────────────┐           
│\n│   │              MERKLE TREE LAYER (Batched)                    │          
│\n│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │           
│\n│   │  │  Batch 1    │  │  Batch 2    │  │  Batch N    │         │           
│\n│   │  │  Root: 0x.. │  │  Root: 0x.. │  │  Root: 0x.. │         │           
│\n│   │  │  1000 votes │  │  1000 votes │  │  1000 votes │         │           
│\n│   │  └─────────────┘  └─────────────┘  └─────────────┘         │           
│\n│   └────────────────────────────────────────────────────────────┘           
│\n│                              │                                             
│\n│                              ▼                                             
│\n│   ┌────────────────────────────────────────────────────────────┐           
│\n│   │              EXTERNAL SIGNATURE LAYER (Optional)            │          
│\n│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │           
│\n│   │  │  Signify    │  │  OpenPubKey │  │  Anchoring  │         │           
│\n│   │  │  (Sigstore) │  │  (SSH/PGP)  │  │  (Optional) │         │           
│\n│   │  └─────────────┘  └─────────────┘  └─────────────┘         │           
│\n│   └────────────────────────────────────────────────────────────┘           
│\n│                                                                            
│\n└────────────────────────────────────────────────────────────────────────────
─┘\n```\n\n### 1.4 Database Schema Extensions\n\n```sql\n-- 
============================================================\n-- MIGRATION 010: 
Immutable Vote Ledger\n-- 
============================================================\n\n-- Vote ledger: 
Append-only, hash-chained record of all votes\nCREATE TABLE vote_ledger (\n    
id              INTEGER PRIMARY KEY AUTOINCREMENT,\n    \n    -- Vote 
reference\n    fact_id         INTEGER NOT NULL REFERENCES facts(id),\n    
agent_id        TEXT NOT NULL REFERENCES agents(id),\n    vote            
INTEGER NOT NULL,  -- +1 (verify), -1 (dispute)\n    vote_weight     REAL NOT 
NULL,\n    \n    -- Cryptographic chain\n    prev_hash       TEXT NOT NULL,     
-- Previous vote ledger entry hash\n    hash            TEXT NOT NULL,      -- 
SHA-256 of this entry\n    \n    -- Temporal proof\n    timestamp       TEXT NOT
NULL DEFAULT (datetime(\'now\')),\n    \n    -- Optional: External 
verification\n    signature       TEXT,               -- Ed25519 signature by 
agent\n    \n    -- Index for efficient verification\n    
UNIQUE(hash)\n);\n\nCREATE INDEX idx_vote_ledger_fact ON 
vote_ledger(fact_id);\nCREATE INDEX idx_vote_ledger_agent ON 
vote_ledger(agent_id);\nCREATE INDEX idx_vote_ledger_timestamp ON 
vote_ledger(timestamp);\n\n-- Merkle tree roots for periodic integrity 
verification\nCREATE TABLE vote_merkle_roots (\n    id              INTEGER 
PRIMARY KEY AUTOINCREMENT,\n    root_hash       TEXT NOT NULL,              -- 
SHA-256 of combined vote hashes\n    vote_start_id   INTEGER NOT NULL,          
-- First vote in this batch\n    vote_end_id     INTEGER NOT NULL,           -- 
Last vote in this batch\n    vote_count      INTEGER NOT NULL,\n    created_at  
TEXT NOT NULL DEFAULT (datetime(\'now\')),\n    \n    -- Optional: External 
proof-of-existence\n    external_proof  TEXT,                       -- URL or 
hash of external anchor\n    \n    -- Signature by "God Key" (if configured)\n  
signature       TEXT                        -- Ed25519 signature of 
root_hash\n);\n\nCREATE INDEX idx_vote_merkle_range ON 
vote_merkle_roots(vote_start_id, vote_end_id);\n\n-- Audit log export 
tracking\nCREATE TABLE vote_audit_exports (\n    id              INTEGER PRIMARY
KEY AUTOINCREMENT,\n    export_type     TEXT NOT NULL,              -- \'json\',
\'csv\', \'chain\'\n    filename        TEXT NOT NULL,\n    file_hash       TEXT
NOT NULL,              -- SHA-256 of exported file\n    vote_start_id   INTEGER 
NOT NULL,\n    vote_end_id     INTEGER NOT NULL,\n    exported_at     TEXT NOT 
NULL DEFAULT (datetime(\'now\')),\n    exported_by     TEXT NOT NULL            
-- API key or agent ID\n);\n\n-- Tamper detection log (append-only by 
design)\nCREATE TABLE vote_integrity_checks (\n    id              INTEGER 
PRIMARY KEY AUTOINCREMENT,\n    check_type      TEXT NOT NULL,              -- 
\'merkle\', \'chain\', \'full\'\n    status          TEXT NOT NULL,             
-- \'ok\', \'violation\', \'error\'\n    details         TEXT,                  
-- JSON with findings\n    started_at      TEXT NOT NULL,\n    completed_at    
TEXT NOT NULL\n);\n```\n\n### 1.5 Implementation: Immutable Vote 
Ledger\n\n```python\n# cortex/vote_ledger.py\n"""\nImmutable Vote Ledger — 
Cryptographic integrity for CORTEX consensus votes.\n\nFeatures:\n- Hash-chained
vote entries\n- Periodic Merkle tree generation\n- Tamper detection via hash 
verification\n- Export with integrity proofs\n"""\n\nimport hashlib\nimport 
json\nimport sqlite3\nfrom typing import List, Optional, Tuple\nfrom dataclasses
import dataclass\nfrom datetime import datetime\n\n\n@dataclass\nclass 
VoteEntry:\n    """A single entry in the vote ledger."""\n    id: int\n    
fact_id: int\n    agent_id: str\n    vote: int\n    vote_weight: float\n    
prev_hash: str\n    hash: str\n    timestamp: str\n    signature: Optional[str] 
= None\n\n\nclass VoteLedger:\n    """\n    Manages the cryptographic integrity 
of CORTEX consensus votes.\n    \n    Features:\n    - Append-only hash-chained 
vote storage\n    - Periodic Merkle tree generation\n    - Tamper detection via 
hash verification\n    - Export with integrity proofs\n    """\n    \n    
MERKLE_BATCH_SIZE = 1000  # Create Merkle root every N votes\n    \n    def 
__init__(self, conn: sqlite3.Connection):\n        self.conn = conn\n    \n    
def _compute_hash(\n        self,\n        prev_hash: str,\n        fact_id: 
int,\n        agent_id: str,\n        vote: int,\n        vote_weight: float,\n 
timestamp: str\n    ) -> str:\n        """Compute the hash for a vote 
entry."""\n        hash_input = 
f"{prev_hash}:{fact_id}:{agent_id}:{vote}:{vote_weight}:{timestamp}"\n        
return hashlib.sha256(hash_input.encode()).hexdigest()\n    \n    def 
append_vote(\n        self,\n        fact_id: int,\n        agent_id: str,\n    
vote: int,\n        vote_weight: float,\n        signature: Optional[str] = 
None\n    ) -> VoteEntry:\n        """\n        Append a vote to the immutable 
ledger.\n        \n        Args:\n            fact_id: The fact being voted on\n
agent_id: The voting agent\n            vote: +1 (verify) or -1 (dispute)\n     
vote_weight: The weight of the vote (reputation-based)\n            signature: 
Optional cryptographic signature\n            \n        Returns:\n            
The created VoteEntry with computed hash\n        """\n        # Get previous 
hash\n        prev = self.conn.execute(\n            "SELECT hash FROM 
vote_ledger ORDER BY id DESC LIMIT 1"\n        ).fetchone()\n        prev_hash =
prev[0] if prev else "GENESIS"\n        \n        # Compute timestamp\n        
timestamp = datetime.utcnow().isoformat()\n        \n        # Compute hash\n   
entry_hash = self._compute_hash(\n            prev_hash, fact_id, agent_id, 
vote, vote_weight, timestamp\n        )\n        \n        # Insert vote entry\n
cursor = self.conn.execute(\n            """\n            INSERT INTO 
vote_ledger \n            (fact_id, agent_id, vote, vote_weight, prev_hash, 
hash, timestamp, signature)\n            VALUES (?, ?, ?, ?, ?, ?, ?, ?)\n      
""",\n            (fact_id, agent_id, vote, vote_weight, prev_hash, entry_hash, 
timestamp, signature)\n        )\n        \n        # Check if we need to create
a Merkle checkpoint\n        self._maybe_create_checkpoint()\n        \n        
return VoteEntry(\n            id=cursor.lastrowid,\n            
fact_id=fact_id,\n            agent_id=agent_id,\n            vote=vote,\n      
vote_weight=vote_weight,\n            prev_hash=prev_hash,\n            
hash=entry_hash,\n            timestamp=timestamp,\n            
signature=signature\n        )\n    \n    def _maybe_create_checkpoint(self) -> 
Optional[int]:\n        """Create a Merkle checkpoint if batch size is 
reached."""\n        # Count votes since last checkpoint\n        last = 
self.conn.execute(\n            "SELECT MAX(vote_end_id) FROM 
vote_merkle_roots"\n        ).fetchone()[0] or 0\n        \n        count = 
self.conn.execute(\n            "SELECT COUNT(*) FROM vote_ledger WHERE id > 
?",\n            (last,)\n        ).fetchone()[0]\n        \n        if count < 
self.MERKLE_BATCH_SIZE:\n            return None\n        \n        return 
self.create_merkle_checkpoint()\n    \n    def create_merkle_checkpoint(self) ->
Optional[int]:\n        """\n        Create a Merkle tree checkpoint for recent 
votes.\n        Returns the checkpoint ID or None if no new votes.\n        
"""\n        # Find last checkpoint\n        last = self.conn.execute(\n        
"SELECT MAX(vote_end_id) FROM vote_merkle_roots"\n        ).fetchone()[0] or 0\n
\n        # Get range of votes to include\n        start = last + 1\n        
end_row = self.conn.execute(\n            "SELECT id FROM vote_ledger WHERE id >
? ORDER BY id LIMIT 1 OFFSET ?",\n            (last, self.MERKLE_BATCH_SIZE - 
1)\n        ).fetchone()\n        end = end_row[0] if end_row else start\n      
\n        # Compute Merkle root\n        root = self._compute_merkle_root(start,
end)\n        if not root:\n            return None\n        \n        # Store 
checkpoint\n        cursor = self.conn.execute(\n            """INSERT INTO 
vote_merkle_roots \n                (root_hash, vote_start_id, vote_end_id, 
vote_count) \n                VALUES (?, ?, ?, ?)""",\n            (root, start,
end, end - start + 1)\n        )\n        \n        return cursor.lastrowid\n   
\n    def _compute_merkle_root(self, start_id: int, end_id: int) -> 
Optional[str]:\n        """Compute Merkle root for a range of votes."""\n       
cursor = self.conn.execute(\n            "SELECT hash FROM vote_ledger WHERE id 
>= ? AND id <= ? ORDER BY id",\n            (start_id, end_id)\n        )\n     
hashes = [row[0] for row in cursor.fetchall()]\n        \n        if not 
hashes:\n            return None\n        \n        # Build Merkle tree\n       
while len(hashes) > 1:\n            next_level = []\n            for i in 
range(0, len(hashes), 2):\n                left = hashes[i]\n                
right = hashes[i + 1] if i + 1 < len(hashes) else hashes[i]\n                
combined = hashlib.sha256((left + right).encode()).hexdigest()\n                
next_level.append(combined)\n            hashes = next_level\n        \n        
return hashes[0]\n    \n    def verify_chain_integrity(self) -> dict:\n        
"""\n        Verify the integrity of the entire vote ledger.\n        \n        
Returns:\n            Dict with verification results\n        """\n        
violations = []\n        \n        # 1. Verify hash chain continuity\n        
votes = self.conn.execute(\n            "SELECT id, prev_hash, hash, fact_id, 
agent_id, vote, vote_weight, timestamp "\n            "FROM vote_ledger ORDER BY
id"\n        ).fetchall()\n        \n        prev_hash = "GENESIS"\n        for 
vote in votes:\n            vote_id, tx_prev, tx_hash, fact_id, agent_id, 
vote_val, weight, ts = vote\n            \n            # Verify prev_hash 
matches\n            if tx_prev != prev_hash:\n                
violations.append({\n                    "vote_id": vote_id,\n                  
"type": "chain_break",\n                    "expected_prev": prev_hash,\n       
"actual_prev": tx_prev\n                })\n            \n            # Verify 
current hash\n            computed = self._compute_hash(\n                
tx_prev, fact_id, agent_id, vote_val, weight, ts\n            )\n            \n 
if computed != tx_hash:\n                violations.append({\n                  
"vote_id": vote_id,\n                    "type": "hash_mismatch",\n             
"computed": computed,\n                    "stored": tx_hash\n                
})\n            \n            prev_hash = tx_hash\n        \n        # 2. Verify
Merkle roots\n        merkles = self.conn.execute(\n            "SELECT id, 
root_hash, vote_start_id, vote_end_id FROM vote_merkle_roots ORDER BY id"\n     
).fetchall()\n        \n        for m in merkles:\n            m_id, 
stored_root, start, end = m\n            computed_root = 
self._compute_merkle_root(start, end)\n            \n            if 
computed_root != stored_root:\n                violations.append({\n            
"merkle_id": m_id,\n                    "type": "merkle_mismatch",\n            
"range": f"{start}-{end}",\n                    "computed": computed_root,\n    
"stored": stored_root\n                })\n        \n        return {\n         
"valid": len(violations) == 0,\n            "violations": violations,\n         
"votes_checked": len(votes),\n            "merkle_roots_checked": len(merkles)\n
}\n    \n    def get_vote_history(self, fact_id: int) -> List[VoteEntry]:\n     
"""Get the complete vote history for a fact."""\n        cursor = 
self.conn.execute(\n            "SELECT id, fact_id, agent_id, vote, 
vote_weight, prev_hash, hash, timestamp, signature "\n            "FROM 
vote_ledger WHERE fact_id = ? ORDER BY id",\n            (fact_id,)\n        )\n
\n        return [\n            VoteEntry(\n                id=row[0],\n        
fact_id=row[1],\n                agent_id=row[2],\n                
vote=row[3],\n                vote_weight=row[4],\n                
prev_hash=row[5],\n                hash=row[6],\n                
timestamp=row[7],\n                signature=row[8]\n            )\n            
for row in cursor.fetchall()\n        ]\n    \n    def 
export_verifiable_log(self, output_path: str, start_id: int = 1) -> dict:\n     
"""\n        Export votes with integrity proofs.\n        \n        Args:\n     
output_path: Where to write the export (JSON format)\n            start_id: 
Starting vote ID\n            \n        Returns:\n            Export metadata 
with root hash for verification\n        """\n        votes = 
self.conn.execute(\n            "SELECT * FROM vote_ledger WHERE id >= ? ORDER 
BY id",\n            (start_id,)\n        ).fetchall()\n        \n        # 
Build Merkle tree\n        hashes = [v[6] for v in votes]  # hash column\n      
\n        # Compute root\n        root = hashes[0] if hashes else None\n        
while len(hashes) > 1:\n            next_level = []\n            for i in 
range(0, len(hashes), 2):\n                left = hashes[i]\n                
right = hashes[i + 1] if i + 1 < len(hashes) else hashes[i]\n                
combined = hashlib.sha256((left + right).encode()).hexdigest()\n                
next_level.append(combined)\n            hashes = next_level\n            root =
hashes[0] if hashes else None\n        \n        export_data = {\n            
"export": {\n                "version": "1.0",\n                "exported_at": 
datetime.utcnow().isoformat(),\n                "start_id": start_id,\n         
"end_id": votes[-1][0] if votes else start_id,\n                "vote_count": 
len(votes),\n                "merkle_root": root\n            },\n            
"votes": [\n                {\n                    "id": v[0],\n                
"fact_id": v[1],\n                    "agent_id": v[2],\n                    
"vote": v[3],\n                    "vote_weight": v[4],\n                    
"prev_hash": v[5],\n                    "hash": v[6],\n                    
"timestamp": v[7],\n                    "signature": v[8]\n                }\n  
for v in votes\n            ]\n        }\n        \n        with 
open(output_path, \'w\') as f:\n            json.dump(export_data, f, 
indent=2)\n        \n        # Compute file hash\n        with open(output_path,
\'rb\') as f:\n            file_hash = hashlib.sha256(f.read()).hexdigest()\n   
\n        # Record export\n        self.conn.execute(\n            """INSERT 
INTO vote_audit_exports \n                (export_type, filename, file_hash, 
vote_start_id, vote_end_id, exported_by)\n                VALUES (?, ?, ?, ?, ?,
?)""",\n            ("json", output_path, file_hash, \n             
export_data["export"]["start_id"],\n             
export_data["export"]["end_id"],\n             "system")\n        )\n        
self.conn.commit()\n        \n        return {\n            "output_path": 
output_path,\n            "file_hash": file_hash,\n            "merkle_root": 
root,\n            "votes": len(votes)\n        }\n```\n\n### 1.6 CLI 
Commands\n\n```bash\n# Create a Merkle checkpoint for votes\ncortex vote-ledger 
checkpoint\n\n# Verify vote ledger integrity\ncortex vote-ledger verify\n# 
Output: ✓ Chain valid (10,234 votes, 10 Merkle roots)\n#         ✓ All Merkle 
roots verified\n#         ✓ No tampering detected\n\n# Export verifiable vote 
log\ncortex vote-ledger export --format json --output votes_2024.json\n\n# Get 
vote history for a fact\ncortex vote-ledger history <fact_id>\n\n# Import and 
verify external vote log\ncortex vote-ledger verify-external 
votes_2024.json\n```\n\n---\n\n## 2. High-Availability Ledger 
Synchronization\n\n### 2.1 Problem Statement\n\nCurrent CORTEX operates as a 
single-node system with no replication:\n\n```\nCurrent 
State:\n┌─────────────┐\n│  CORTEX     │\n│  (Single)   │\n│  SQLite     
│\n└─────────────┘\n     │\n     ▼\n  [SPOF]  ← Single Point of 
Failure\n```\n\n**Limitations:**\n- ❌ No failover capability\n- ❌ No 
geographic distribution\n- ❌ Consensus votes lost if node fails\n- ❌ No read 
replicas for query scaling\n\n### 2.2 Design Goals\n\n| Goal | Priority | 
Description |\n|------|----------|-------------|\n| **Availability** | P0 | 
99.9% uptime with automatic failover |\n| **Consistency** | P0 | Strong 
consistency for votes, eventual for reads |\n| **Partition Tolerance** | P0 | 
Continue operating during network splits |\n| **Conflict Resolution** | P1 | 
Automatic merge for concurrent writes |\n| **Scalability** | P2 | Horizontal 
scaling for read-heavy workloads |\n\n### 2.3 Architecture: CRDT-Based 
Replication\n\n```\n┌───────────────────────────────────────────────────────────
──────────────────┐\n│                    HIGH-AVAILABILITY CORTEX CLUSTER      
│\n├────────────────────────────────────────────────────────────────────────────
─┤\n│                                                                           
   │\n│   ┌───────────────────────────────────────────────────────────────────┐ 
│\n│   │                    CONSENSUS LAYER (Raft)                          │   
│\n│   │  ┌─────────┐  ┌─────────┐  ┌─────────┐                           │    
│\n│   │  │  Node 1 │  │  Node 2 │  │  Node 3 │  ← Leader Election         │    
│\n│   │  │  Leader │◄─┤ Follower│◄─┤ Follower│                           │    
│\n│   │  └────┬────┘  └────┬────┘  └────┬────┘                           │    
│\n│   │       └─────────────┴─────────────┘                              │    
│\n│   │                     │                                            │    
│\n│   │                     ▼                                            │    
│\n│   │         ┌─────────────────────┐                                  │    
│\n│   │         │   Log Replication   │                                  │    
│\n│   │         │   (Strong Consistency)│                                │    
│\n│   │         └─────────────────────┘                                  │    
│\n│   └───────────────────────────────────────────────────────────────────┘    
│\n│                                    │                                       
│\n│                                    ▼                                       
│\n│   ┌───────────────────────────────────────────────────────────────────┐    
│\n│   │                    DATA LAYER (CRDT)                               │   
│\n│   │                                                                    │   
│\n│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │    
│\n│   │  │   Node 1     │  │   Node 2     │  │   Node 3     │             │    
│\n│   │  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │             │    
│\n│   │  │ │  Facts   │ │  │ │  Facts   │ │  │ │  Facts   │ │             │    
│\n│   │  │ │ (CRDT)   │◄┼──┼►│ (CRDT)   │◄┼──┼►│ (CRDT)   │ │             │    
│\n│   │  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │             │    
│\n│   │  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │             │    
│\n│   │  │ │  Votes   │ │  │ │  Votes   │ │  │ │  Votes   │ │             │    
│\n│   │  │ │ (CRDT)   │◄┼──┼►│ (CRDT)   │◄┼──┼►│ (CRDT)   │ │             │    
│\n│   │  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │             │    
│\n│   │  └──────────────┘  └──────────────┘  └──────────────┘             │    
│\n│   │                                                                    │   
│\n│   │  Replication: Anti-entropy gossip (every 30s)                     │    
│\n│   │  Conflict Resolution: LWW for facts, OR-Set for votes             │    
│\n│   └───────────────────────────────────────────────────────────────────┘    
│\n│                                                                            
│\n│   ┌───────────────────────────────────────────────────────────────────┐    
│\n│   │                    SYNC PROTOCOL                                   │   
│\n│   │                                                                    │   
│\n│   │  1. Vector Clocks: Track causality across nodes                   │    
│\n│   │  2. Merkle Trees: Efficient diff for synchronization              │    
│\n│   │  3. Bloom Filters: Quick "has this changed?" checks               │    
│\n│   │  4. Gossip Protocol: Epidemic broadcast for updates               │    
│\n│   └───────────────────────────────────────────────────────────────────┘    
│\n│                                                                            
│\n└────────────────────────────────────────────────────────────────────────────
─┘\n```\n\n### 2.4 Database Schema Extensions\n\n```sql\n-- 
============================================================\n-- MIGRATION 011: 
High-Availability Synchronization\n-- 
============================================================\n\n-- Node identity
and cluster membership\nCREATE TABLE cluster_nodes (\n    node_id         TEXT 
PRIMARY KEY,\n    node_name       TEXT NOT NULL,\n    node_address    TEXT NOT 
NULL,          -- Host:port for communication\n    node_region     TEXT,        
-- Geographic region\n    is_active       BOOLEAN DEFAULT TRUE,\n    is_voter   
BOOLEAN DEFAULT TRUE,   -- Participates in Raft consensus\n    joined_at       
TEXT NOT NULL DEFAULT (datetime(\'now\')),\n    last_seen_at    TEXT NOT NULL 
DEFAULT (datetime(\'now\')),\n    raft_role       TEXT,                   -- 
\'leader\', \'follower\', \'candidate\'\n    meta            TEXT DEFAULT 
\'{}\'\n);\n\n-- Vector clocks for causality tracking\nCREATE TABLE 
vector_clocks (\n    node_id         TEXT NOT NULL REFERENCES 
cluster_nodes(node_id),\n    entity_type     TEXT NOT NULL,          -- 
\'fact\', \'vote\', \'agent\'\n    entity_id       TEXT NOT NULL,          -- ID
of the entity\n    version         INTEGER NOT NULL DEFAULT 0,\n    timestamp   
TEXT NOT NULL DEFAULT (datetime(\'now\')),\n    PRIMARY KEY (node_id, 
entity_type, entity_id)\n);\n\n-- Sync log for anti-entropy\nCREATE TABLE 
sync_log (\n    id              INTEGER PRIMARY KEY AUTOINCREMENT,\n    node_id 
TEXT NOT NULL REFERENCES cluster_nodes(node_id),\n    sync_type       TEXT NOT 
NULL,          -- \'push\', \'pull\', \'full\'\n    entity_type     TEXT NOT 
NULL,\n    entity_count    INTEGER NOT NULL,\n    started_at      TEXT NOT 
NULL,\n    completed_at    TEXT,\n    status          TEXT,                   --
\'success\', \'failed\', \'partial\'\n    details         TEXT                  
-- JSON with sync details\n);\n\nCREATE INDEX idx_sync_log_node ON 
sync_log(node_id, completed_at);\n\n-- Conflict resolution log\nCREATE TABLE 
conflict_log (\n    id              INTEGER PRIMARY KEY AUTOINCREMENT,\n    
entity_type     TEXT NOT NULL,\n    entity_id       TEXT NOT NULL,\n    
conflict_type   TEXT NOT NULL,          -- \'concurrent_update\', 
\'delete_update\'\n    node_a          TEXT NOT NULL,\n    node_b          TEXT 
NOT NULL,\n    resolution      TEXT NOT NULL,          -- \'lww\', \'merge\', 
\'manual\'\n    resolved_at     TEXT NOT NULL DEFAULT (datetime(\'now\')),\n    
details         TEXT\n);\n\n-- Merkle tree for efficient diff\nCREATE TABLE 
sync_merkle (\n    node_id         TEXT NOT NULL,\n    entity_type     TEXT NOT 
NULL,\n    bucket          INTEGER NOT NULL,       -- Hash bucket\n    
merkle_root     TEXT NOT NULL,\n    updated_at      TEXT NOT NULL DEFAULT 
(datetime(\'now\')),\n    PRIMARY KEY (node_id, entity_type, 
bucket)\n);\n```\n\n### 2.5 Implementation: HA Synchronization\n\n```python\n# 
cortex/ha_sync.py\n"""\nHigh-Availability Synchronization for 
CORTEX.\n\nFeatures:\n- Raft consensus for leader election\n- CRDT-based data 
replication\n- Anti-entropy gossip protocol\n- Automatic conflict 
resolution\n"""\n\nimport hashlib\nimport json\nimport sqlite3\nimport 
asyncio\nfrom typing import Dict, List, Optional, Set, Tuple\nfrom dataclasses 
import dataclass, asdict\nfrom datetime import datetime\nfrom enum import 
Enum\nimport random\n\n\nclass NodeRole(Enum):\n    LEADER = "leader"\n    
FOLLOWER = "follower"\n    CANDIDATE = "candidate"\n\n\n@dataclass\nclass 
VectorClock:\n    """Vector clock for causality tracking."""\n    node_id: str\n
counters: Dict[str, int]\n    \n    def increment(self) -> "VectorClock":\n     
"""Increment this node\'s counter."""\n        new_counters = 
self.counters.copy()\n        new_counters[self.node_id] = 
new_counters.get(self.node_id, 0) + 1\n        return VectorClock(self.node_id, 
new_counters)\n    \n    def compare(self, other: "VectorClock") -> 
Optional[str]:\n        """\n        Compare two vector clocks.\n        
Returns: \'before\', \'after\', \'concurrent\', or \'equal\'\n        """\n     
all_nodes = set(self.counters.keys()) | set(other.counters.keys())\n        \n  
dominates = False\n        dominated = False\n        \n        for node in 
all_nodes:\n            a = self.counters.get(node, 0)\n            b = 
other.counters.get(node, 0)\n            \n            if a > b:\n              
dominates = True\n            elif b > a:\n                dominated = True\n   
\n        if dominates and not dominated:\n            return "after"\n        
elif dominated and not dominates:\n            return "before"\n        elif not
dominates and not dominated:\n            return "equal"\n        else:\n       
return "concurrent"\n\n\n@dataclass\nclass SyncState:\n    """Current 
synchronization state."""\n    node_id: str\n    role: NodeRole\n    leader_id: 
Optional[str]\n    term: int\n    last_heartbeat: datetime\n    known_nodes: 
List[str]\n\n\nclass HASyncManager:\n    """\n    Manages high-availability 
synchronization for CORTEX.\n    \n    Features:\n    - Raft consensus for 
leader election\n    - CRDT-based conflict-free replication\n    - Anti-entropy 
gossip protocol\n    """\n    \n    def __init__(\n        self,\n        conn: 
sqlite3.Connection,\n        node_id: str,\n        node_address: str,\n        
peers: List[str],\n        gossip_interval: float = 30.0\n    ):\n        
self.conn = conn\n        self.node_id = node_id\n        self.node_address = 
node_address\n        self.peers = peers\n        self.gossip_interval = 
gossip_interval\n        \n        self.role = NodeRole.FOLLOWER\n        
self.leader_id: Optional[str] = None\n        self.term = 0\n        
self.voted_for: Optional[str] = None\n        \n        self._running = False\n 
self._gossip_task: Optional[asyncio.Task] = None\n    \n    def 
initialize_node(self) -> None:\n        """Register this node in the 
cluster."""\n        self.conn.execute(\n            """\n            INSERT OR 
REPLACE INTO cluster_nodes \n            (node_id, node_name, node_address, 
is_active, raft_role)\n            VALUES (?, ?, ?, TRUE, ?)\n            """,\n
(self.node_id, self.node_id, self.node_address, self.role.value)\n        )\n   
self.conn.commit()\n    \n    async def start(self) -> None:\n        """Start 
the HA sync manager."""\n        self._running = True\n        
self.initialize_node()\n        \n        # Start gossip protocol\n        
self._gossip_task = asyncio.create_task(self._gossip_loop())\n        \n        
# Start Raft election timeout\n        asyncio.create_task(self._raft_loop())\n 
\n    async def stop(self) -> None:\n        """Stop the HA sync manager."""\n  
self._running = False\n        if self._gossip_task:\n            
self._gossip_task.cancel()\n    \n    async def _gossip_loop(self) -> None:\n   
"""Background task for anti-entropy gossip."""\n        while self._running:\n  
try:\n                await self._perform_gossip()\n            except Exception
as e:\n                print(f"Gossip error: {e}")\n            \n            
await asyncio.sleep(self.gossip_interval)\n    \n    async def 
_perform_gossip(self) -> None:\n        """Perform anti-entropy with a random 
peer."""\n        if not self.peers:\n            return\n        \n        # 
Select random peer\n        peer = random.choice(self.peers)\n        \n        
# Get our Merkle roots\n        our_roots = self._get_merkle_roots()\n        \n
# In real implementation, this would be an RPC call\n        # For now, we 
simulate the sync process\n        peer_roots = await 
self._fetch_peer_roots(peer)\n        \n        # Find differences\n        
diffs = self._find_merkle_diffs(our_roots, peer_roots)\n        \n        if 
diffs:\n            # Sync missing data\n            await 
self._sync_differences(peer, diffs)\n    \n    def _get_merkle_roots(self) -> 
Dict[str, Dict[int, str]]:\n        """Get Merkle roots for all entity 
types."""\n        cursor = self.conn.execute(\n            "SELECT entity_type,
bucket, merkle_root FROM sync_merkle WHERE node_id = ?",\n            
(self.node_id,)\n        )\n        \n        roots: Dict[str, Dict[int, str]] =
{}\n        for row in cursor.fetchall():\n            entity_type, bucket, root
= row\n            if entity_type not in roots:\n                
roots[entity_type] = {}\n            roots[entity_type][bucket] = root\n        
\n        return roots\n    \n    async def _fetch_peer_roots(self, peer: str) 
-> Dict[str, Dict[int, str]]:\n        """Fetch Merkle roots from a peer."""\n  
# In real implementation: RPC call to peer\n        # Placeholder for 
demonstration\n        return {}\n    \n    def _find_merkle_diffs(\n        
self,\n        our_roots: Dict[str, Dict[int, str]],\n        peer_roots: 
Dict[str, Dict[int, str]]\n    ) -> List[Tuple[str, int]]:\n        """Find 
buckets that differ between nodes."""\n        diffs = []\n        \n        
all_types = set(our_roots.keys()) | set(peer_roots.keys())\n        \n        
for entity_type in all_types:\n            our_buckets = 
our_roots.get(entity_type, {})\n            peer_buckets = 
peer_roots.get(entity_type, {})\n            \n            all_buckets = 
set(our_buckets.keys()) | set(peer_buckets.keys())\n            \n            
for bucket in all_buckets:\n                our_root = our_buckets.get(bucket)\n
peer_root = peer_buckets.get(bucket)\n                \n                if 
our_root != peer_root:\n                    diffs.append((entity_type, 
bucket))\n        \n        return diffs\n    \n    async def 
_sync_differences(\n        self,\n        peer: str,\n        diffs: 
List[Tuple[str, int]]\n    ) -> None:\n        """Synchronize differences with a
peer."""\n        for entity_type, bucket in diffs:\n            # In real 
implementation: fetch and merge entities\n            pass\n    \n    async def 
_raft_loop(self) -> None:\n        """Raft consensus loop for leader 
election."""\n        while self._running:\n            timeout = 
random.uniform(0.15, 0.3)  # 150-300ms election timeout\n            \n         
await asyncio.sleep(timeout)\n            \n            if self.role == 
NodeRole.FOLLOWER:\n                # Check if we haven\'t heard from leader\n  
# Transition to candidate\n                await self._start_election()\n    \n 
async def _start_election(self) -> None:\n        """Start a Raft election."""\n
self.term += 1\n        self.role = NodeRole.CANDIDATE\n        self.voted_for =
self.node_id\n        \n        # Request votes from peers\n        votes = 1  #
Vote for self\n        \n        for peer in self.peers:\n            # In real 
implementation: RPC call\n            # Placeholder\n            pass\n        
\n        # Check if we won\n        if votes > (len(self.peers) + 1) / 2:\n    
await self._become_leader()\n    \n    async def _become_leader(self) -> None:\n
"""Transition to leader role."""\n        self.role = NodeRole.LEADER\n        
self.leader_id = self.node_id\n        \n        self.conn.execute(\n           
"UPDATE cluster_nodes SET raft_role = ? WHERE node_id = ?",\n            
(NodeRole.LEADER.value, self.node_id)\n        )\n        self.conn.commit()\n  
\n        # Start sending heartbeats\n        
asyncio.create_task(self._send_heartbeats())\n    \n    async def 
_send_heartbeats(self) -> None:\n        """Send heartbeat messages to 
followers."""\n        while self._running and self.role == NodeRole.LEADER:\n  
for peer in self.peers:\n                # In real implementation: RPC call\n   
pass\n            \n            await asyncio.sleep(0.05)  # 50ms heartbeat 
interval\n    \n    def replicate_vote(\n        self,\n        fact_id: int,\n 
agent_id: str,\n        vote: int,\n        vote_weight: float\n    ) -> bool:\n
"""\n        Replicate a vote to the cluster.\n        Only the leader can 
accept writes.\n        """\n        if self.role != NodeRole.LEADER:\n         
# Forward to leader\n            return False\n        \n        # Append to 
local log\n        # Replicate to followers\n        # Wait for majority 
acknowledgment\n        \n        return True\n    \n    def 
update_merkle_tree(self, entity_type: str, entity_id: str) -> None:\n        
"""Update Merkle tree after entity change."""\n        # Compute bucket from 
entity_id hash\n        bucket = 
int(hashlib.md5(entity_id.encode()).hexdigest(), 16) % 256\n        \n        # 
Recompute Merkle root for this bucket\n        # This is simplified - real 
implementation would recompute from entities\n        new_root = 
hashlib.sha256(\n            
f"{entity_type}:{entity_id}:{datetime.utcnow().isoformat()}".encode()\n        
).hexdigest()\n        \n        self.conn.execute(\n            """\n          
INSERT OR REPLACE INTO sync_merkle \n            (node_id, entity_type, bucket, 
merkle_root, updated_at)\n            VALUES (?, ?, ?, ?, datetime(\'now\'))\n  
""",\n            (self.node_id, entity_type, bucket, new_root)\n        )\n    
self.conn.commit()\n```\n\n---\n\n## 3. Edge Deployment via MCP Server 
Optimization\n\n### 3.1 Problem Statement\n\nCurrent MCP server has limitations 
for edge deployment:\n\n| Aspect | Current | Edge Requirement 
|\n|--------|---------|------------------|\n| Transport | stdio only | Multiple 
transports (SSE, WebSocket, HTTP/2) |\n| Concurrency | Blocking | Async with 
connection pooling |\n| Caching | None | Multi-tier caching (LRU, distributed) 
|\n| Batching | None | Multi-fact operations |\n| Observability | Basic logging 
| Metrics, traces, structured logs |\n| Resource Usage | Unbounded | Memory/CPU 
limits for edge devices |\n\n### 3.2 Design Goals\n\n| Goal | Priority | 
Description |\n|------|----------|-------------|\n| **Low Latency** | P0 | <10ms
p99 for cached queries |\n| **High Throughput** | P0 | >1000 req/s per node |\n|
**Resource Efficiency** | P0 | <256MB RAM, <1 CPU core |\n| **Transport 
Flexibility** | P1 | stdio, SSE, WebSocket, HTTP/2 |\n| **Edge Caching** | P1 | 
LRU + distributed cache support |\n| **Observability** | P2 | Prometheus 
metrics, OpenTelemetry traces |\n\n### 3.3 Architecture: Optimized MCP 
Server\n\n```\n┌────────────────────────────────────────────────────────────────
─────────────┐\n│                    EDGE-OPTIMIZED MCP SERVER                  
│\n├────────────────────────────────────────────────────────────────────────────
─┤\n│                                                                           
   │\n│   ┌───────────────────────────────────────────────────────────────────┐ 
│\n│   │                      Transport Layer                               │   
│\n│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐       │    
│\n│   │  │  stdio   │  │   SSE    │  │  HTTP/2  │  │  WebSocket   │       │    
│\n│   │  │(default) │  │ (server) │  │(streaming│  │ (real-time)  │       │    
│\n│   │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘       │    
│\n│   │       └─────────────┴─────────────┴───────────────┘               │    
│\n│   │                         │                                         │    
│\n│   │                         ▼                                         │    
│\n│   │              ┌─────────────────────┐                              │    
│\n│   │              │   Protocol Handler  │                              │    
│\n│   │              │   (MCP 2024-11-05)  │                              │    
│\n│   │              └──────────┬──────────┘                              │    
│\n│   └─────────────────────────┼─────────────────────────────────────────┘    
│\n│                             │                                              
│\n│   ┌─────────────────────────┼─────────────────────────────────────────┐    
│\n│   │              ┌──────────▼──────────┐                               │   
│\n│   │              │    Request Router   │                               │   
│\n│   │              └──────────┬──────────┘                               │   
│\n│   │                         │                                          │   
│\n│   │   ┌─────────────────────┼─────────────────────┐                   │    
│\n│   │   │                     │                     │                   │    
│\n│   │   ▼                     ▼                     ▼                   │    
│\n│   │ ┌──────────┐      ┌──────────┐      ┌──────────────────┐         │    
│\n│   │ │  Tools   │      │Resources │      │  Prompt Templates │         │    
│\n│   │ │ Registry │      │ Registry │      │    Registry      │         │    
│\n│   │ └────┬─────┘      └────┬─────┘      └────────┬─────────┘         │    
│\n│   │      │                 │                     │                   │    
│\n│   └──────┼─────────────────┼─────────────────────┼───────────────────┘    
│\n│          │                 │                     │                         
│\n│   ┌──────▼─────────────────▼─────────────────────▼────────────────────┐   
│\n│   │                     Optimization Layer                             │   
│\n│   │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐     │   
│\n│   │  │  Multi-Tier  │  │   Request    │  │   Connection Pool   │     │   
│\n│   │  │    Cache     │  │   Batching   │  │    (SQLite WAL)     │     │   
│\n│   │  │ ┌──────────┐ │  │              │  │                     │     │   
│\n│   │  │ │  L1:     │ │  │ ┌──────────┐ │  │ ┌─────────────────┐ │     │   
│\n│   │  │ │ In-Memory│ │  │ │  Batch   │ │  │ │  Async Pool     │ │     │   
│\n│   │  │ └──────────┘ │  │ │  Queue   │ │  │ │  (5 conns)      │ │     │   
│\n│   │  │ ┌──────────┐ │  │ └──────────┘ │  │ └─────────────────┘ │     │   
│\n│   │  │ │  L2:     │ │  │              │  │                     │     │   
│\n│   │  │ │  Redis   │ │  │ Flush: 10ms  │  │                     │     │   
│\n│   │  │ │(optional)│ │  │ Max: 100 ops │  │                     │     │   
│\n│   │  │ └──────────┘ │  │              │  │                     │     │   
│\n│   │  └──────────────┘  └──────────────┘  └─────────────────────┘     │   
│\n│   │                                                                    │   
│\n│   │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐     │   
│\n│   │  │   Circuit    │  │   Resource   │  │     Metrics         │     │   
│\n│   │  │   Breaker    │  │    Limits    │  │   (Prometheus)      │     │   
│\n│   │  │              │  │              │  │                     │     │   
│\n│   │  │ Failure: 5   │  │ Memory: 256MB│  │ - Request latency   │     │   
│\n│   │  │ Timeout: 30s │  │ CPU: 1 core  │  │ - Cache hit rate    │     │   
│\n│   │  │ Cooldown: 5s │  │ Conns: 100   │  │ - Error rate        │     │   
│\n│   │  └──────────────┘  └──────────────┘  └─────────────────────┘     │   
│\n│   └────────────────────────────────────────────────────────────────────┘   
│\n│                                                                            
│\n│   ┌───────────────────────────────────────────────────────────────────┐    
│\n│   │                      Engine Layer                                  │   
│\n│   │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐     │    
│\n│   │  │Query Cache   │  │ Write-Ahead  │  │   Embedding Cache   │     │    
│\n│   │  │   (LRU)      │  │   Buffer     │  │    (LRU 100)        │     │    
│\n│   │  └──────────────┘  └──────────────┘  └─────────────────────┘     │    
│\n│   └───────────────────────────────────────────────────────────────────┘    
│\n│                                                                            
│\n└────────────────────────────────────────────────────────────────────────────
─┘\n```\n\n### 3.4 Implementation: Edge-Optimized MCP Server\n\n```python\n# 
cortex/mcp_server_edge.py\n"""\nCORTEX MCP Server Edge — High-Performance 
Multi-Transport Implementation.\n\nFeatures:\n- Async I/O with connection 
pooling\n- Multiple transports (stdio, SSE, WebSocket, HTTP/2)\n- Multi-tier 
caching (L1 in-memory, L2 Redis)\n- Request batching\n- Circuit breaker 
pattern\n- Resource limits\n- Comprehensive metrics\n"""\n\nfrom __future__ 
import annotations\n\nimport asyncio\nimport json\nimport logging\nimport 
time\nimport resource\nfrom contextlib import asynccontextmanager\nfrom 
dataclasses import dataclass, field\nfrom functools import lru_cache\nfrom 
typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union\nfrom 
enum import Enum\n\nimport sqlite3\nfrom concurrent.futures import 
ThreadPoolExecutor\n\nlogger = logging.getLogger("cortex.mcp.edge")\n\n\n# 
─────────────────────────────────────────────────────────────────────────\n# 
Configuration\n# 
─────────────────────────────────────────────────────────────────────────\n\n@da
taclass\nclass EdgeMCPConfig:\n    """Configuration for edge-optimized MCP 
server."""\n    db_path: str = "~/.cortex/cortex.db"\n    max_workers: int = 4\n
\n    # Caching\n    query_cache_size: int = 1000\n    embedding_cache_size: int
= 100\n    cache_ttl_seconds: float = 300.0  # 5 minutes\n    \n    # Batching\n
batch_size: int = 100\n    batch_flush_ms: float = 10.0\n    \n    # Resource 
limits\n    max_memory_mb: int = 256\n    max_connections: int = 100\n    \n    
# Circuit breaker\n    circuit_failure_threshold: int = 5\n    
circuit_timeout_seconds: float = 30.0\n    circuit_cooldown_seconds: float = 
5.0\n    \n    # Metrics\n    enable_metrics: bool = True\n    metrics_port: int
= 9090\n    \n    # Transport\n    transport: str = "stdio"  # "stdio", "sse", 
"websocket", "http2"\n    host: str = "127.0.0.1"\n    port: int = 9999\n    
keepalive_interval: float = 30.0\n\n\n# 
─────────────────────────────────────────────────────────────────────────\n# 
Circuit Breaker\n# 
─────────────────────────────────────────────────────────────────────────\n\ncla
ss CircuitState(Enum):\n    CLOSED = "closed"       # Normal operation\n    OPEN
= "open"          # Failing, reject requests\n    HALF_OPEN = "half_open"  # 
Testing if recovered\n\n\nclass CircuitBreaker:\n    """Circuit breaker pattern 
for fault tolerance."""\n    \n    def __init__(\n        self,\n        
failure_threshold: int = 5,\n        timeout_seconds: float = 30.0,\n        
cooldown_seconds: float = 5.0\n    ):\n        self.failure_threshold = 
failure_threshold\n        self.timeout_seconds = timeout_seconds\n        
self.cooldown_seconds = cooldown_seconds\n        \n        self.state = 
CircuitState.CLOSED\n        self.failures = 0\n        self.last_failure_time: 
Optional[float] = None\n        self._lock = asyncio.Lock()\n    \n    async def
call(self, func: Callable, *args, **kwargs) -> Any:\n        """Execute function
with circuit breaker protection."""\n        async with self._lock:\n           
if self.state == CircuitState.OPEN:\n                if time.time() - 
(self.last_failure_time or 0) > self.cooldown_seconds:\n                    
self.state = CircuitState.HALF_OPEN\n                else:\n                    
raise Exception("Circuit breaker is OPEN")\n        \n        try:\n            
result = await asyncio.wait_for(\n                func(*args, **kwargs),\n      
timeout=self.timeout_seconds\n            )\n            \n            async 
with self._lock:\n                if self.state == CircuitState.HALF_OPEN:\n    
self.state = CircuitState.CLOSED\n                self.failures = 0\n           
\n            return result\n            \n        except Exception as e:\n     
async with self._lock:\n                self.failures += 1\n                
self.last_failure_time = time.time()\n                \n                if 
self.failures >= self.failure_threshold:\n                    self.state = 
CircuitState.OPEN\n            \n            raise\n\n\n# 
─────────────────────────────────────────────────────────────────────────\n# 
Multi-Tier Cache\n# 
─────────────────────────────────────────────────────────────────────────\n\ncla
ss MultiTierCache:\n    """\n    Multi-tier cache with L1 (in-memory) and L2 
(Redis) layers.\n    For edge deployment, L2 is optional.\n    """\n    \n    
def __init__(\n        self,\n        l1_size: int = 1000,\n        ttl_seconds:
float = 300.0,\n        redis_url: Optional[str] = None\n    ):\n        
self.l1_size = l1_size\n        self.ttl_seconds = ttl_seconds\n        
self._l1: Dict[str, tuple[Any, float]] = {}\n        self._lock = 
asyncio.Lock()\n        \n        # L2 cache (Redis) - optional for edge\n      
self._l2 = None\n        if redis_url:\n            try:\n                import
redis.asyncio as redis\n                self._l2 = redis.from_url(redis_url)\n  
except ImportError:\n                logger.warning("Redis not available, using 
L1 cache only")\n    \n    def _key(self, prefix: str, **params) -> str:\n      
"""Generate cache key from parameters."""\n        sorted_params = 
sorted(params.items())\n        param_str = json.dumps(sorted_params, 
sort_keys=True)\n        return 
f"{prefix}:{hashlib.md5(param_str.encode()).hexdigest()}"\n    \n    async def 
get(self, key: str) -> Optional[Any]:\n        """Get value from cache."""\n    
now = time.time()\n        \n        # Check L1\n        async with 
self._lock:\n            if key in self._l1:\n                value, expiry = 
self._l1[key]\n                if expiry > now:\n                    return 
value\n                else:\n                    del self._l1[key]\n        \n 
# Check L2 (if available)\n        if self._l2:\n            try:\n             
value = await self._l2.get(key)\n                if value:\n                    
data = json.loads(value)\n                    # Promote to L1\n                 
async with self._lock:\n                        self._l1[key] = (data, now + 
self.ttl_seconds)\n                    return data\n            except Exception
as e:\n                logger.warning("L2 cache error: %s", e)\n        \n      
return None\n    \n    async def set(self, key: str, value: Any) -> None:\n     
"""Set value in cache."""\n        now = time.time()\n        expiry = now + 
self.ttl_seconds\n        \n        # Set L1\n        async with self._lock:\n  
# Evict oldest if at capacity\n            while len(self._l1) >= 
self.l1_size:\n                oldest_key = min(self._l1.keys(), key=lambda k: 
self._l1[k][1])\n                del self._l1[oldest_key]\n            \n       
self._l1[key] = (value, expiry)\n        \n        # Set L2 (if available)\n    
if self._l2:\n            try:\n                await self._l2.setex(\n         
key,\n                    int(self.ttl_seconds),\n                    
json.dumps(value)\n                )\n            except Exception as e:\n      
logger.warning("L2 cache error: %s", e)\n    \n    async def invalidate(self, 
pattern: str) -> None:\n        """Invalidate cache entries matching 
pattern."""\n        async with self._lock:\n            keys_to_remove = [k for
k in self._l1.keys() if pattern in k]\n            for k in keys_to_remove:\n   
del self._l1[k]\n        \n        if self._l2:\n            try:\n             
# Note: This is inefficient, production would use Redis SCAN\n                
pass\n            except Exception as e:\n                logger.warning("L2 
cache error: %s", e)\n\n\n# 
─────────────────────────────────────────────────────────────────────────\n# 
Request Batcher\n# 
─────────────────────────────────────────────────────────────────────────\n\n@da
taclass\nclass BatchItem:\n    """Single item in a batch."""\n    request: 
dict\n    future: asyncio.Future\n\n\nclass RequestBatcher:\n    """Batches 
multiple requests for efficient processing."""\n    \n    def __init__(self, 
max_size: int = 100, flush_ms: float = 10.0):\n        self.max_size = 
max_size\n        self.flush_ms = flush_ms\n        self._batch: List[BatchItem]
= []\n        self._lock = asyncio.Lock()\n        self._flush_task: 
Optional[asyncio.Task] = None\n    \n    async def add(self, request: dict) -> 
asyncio.Future:\n        """Add a request to the batch."""\n        future = 
asyncio.get_event_loop().create_future()\n        item = BatchItem(request, 
future)\n        \n        async with self._lock:\n            
self._batch.append(item)\n            \n            if len(self._batch) >= 
self.max_size:\n                await self._flush()\n            elif 
self._flush_task is None:\n                self._flush_task = 
asyncio.create_task(self._delayed_flush())\n        \n        return future\n   
\n    async def _delayed_flush(self) -> None:\n        """Flush batch after 
delay."""\n        await asyncio.sleep(self.flush_ms / 1000)\n        async with
self._lock:\n            await self._flush()\n            self._flush_task = 
None\n    \n    async def _flush(self) -> None:\n        """Process all batched 
requests."""\n        if not self._batch:\n            return\n        \n       
batch = self._batch[:]\n        self._batch = []\n        \n        # Process 
batch\n        # In real implementation, this would execute batch query\n       
for item in batch:\n            try:\n                result = await 
self._process_single(item.request)\n                
item.future.set_result(result)\n            except Exception as e:\n            
item.future.set_exception(e)\n    \n    async def _process_single(self, request:
dict) -> dict:\n        """Process a single request."""\n        # Placeholder -
real implementation would batch SQL operations\n        return {"status": 
"ok"}\n\n\n# 
─────────────────────────────────────────────────────────────────────────\n# 
Resource Monitor\n# 
─────────────────────────────────────────────────────────────────────────\n\ncla
ss ResourceMonitor:\n    """Monitor and enforce resource limits."""\n    \n    
def __init__(self, max_memory_mb: int = 256, max_connections: int = 100):\n     
self.max_memory_mb = max_memory_mb\n        self.max_connections = 
max_connections\n        self.active_connections = 0\n        self._lock = 
asyncio.Lock()\n    \n    def check_memory(self) -> bool:\n        """Check if 
memory usage is within limits."""\n        try:\n            import psutil\n    
process = psutil.Process()\n            memory_mb = process.memory_info().rss / 
1024 / 1024\n            return memory_mb < self.max_memory_mb\n        except 
ImportError:\n            # Fallback: use resource module\n            import 
resource\n            usage = resource.getrusage(resource.RUSAGE_SELF)\n        
memory_mb = usage.ru_maxrss / 1024  # KB to MB\n            return memory_mb < 
self.max_memory_mb\n    \n    @asynccontextmanager\n    async def 
acquire_connection(self):\n        """Acquire a connection slot."""\n        
async with self._lock:\n            if self.active_connections >= 
self.max_connections:\n                raise Exception("Max connections 
exceeded")\n            self.active_connections += 1\n        \n        try:\n  
yield\n        finally:\n            async with self._lock:\n                
self.active_connections -= 1\n    \n    def get_stats(self) -> dict:\n        
"""Get resource statistics."""\n        try:\n            import psutil\n       
process = psutil.Process()\n            memory_mb = process.memory_info().rss / 
1024 / 1024\n            cpu_percent = process.cpu_percent()\n        except 
ImportError:\n            memory_mb = 0\n            cpu_percent = 0\n        \n
return {\n            "memory_mb": memory_mb,\n            "memory_limit_mb": 
self.max_memory_mb,\n            "active_connections": 
self.active_connections,\n            "max_connections": self.max_connections,\n
"cpu_percent": cpu_percent\n        }\n\n\n# 
─────────────────────────────────────────────────────────────────────────\n# 
Edge-Optimized MCP Server\n# 
─────────────────────────────────────────────────────────────────────────\n\ncla
ss EdgeMCPServer:\n    """\n    Edge-optimized MCP server for CORTEX.\n    \n   
Features:\n    - Multi-tier caching\n    - Request batching\n    - Circuit 
breaker\n    - Resource monitoring\n    - Multiple transports\n    """\n    \n  
def __init__(self, config: Optional[EdgeMCPConfig] = None):\n        self.config
= config or EdgeMCPConfig()\n        self.metrics = MCPMetrics()\n        
self.pool: Optional[AsyncConnectionPool] = None\n        self.executor = 
ThreadPoolExecutor(max_workers=self.config.max_workers)\n        \n        # 
Components\n        self.cache = MultiTierCache(\n            
l1_size=self.config.query_cache_size,\n            
ttl_seconds=self.config.cache_ttl_seconds\n        )\n        self.batcher = 
RequestBatcher(\n            max_size=self.config.batch_size,\n            
flush_ms=self.config.batch_flush_ms\n        )\n        self.circuit = 
CircuitBreaker(\n            
failure_threshold=self.config.circuit_failure_threshold,\n            
timeout_seconds=self.config.circuit_timeout_seconds,\n            
cooldown_seconds=self.config.circuit_cooldown_seconds\n        )\n        
self.resources = ResourceMonitor(\n            
max_memory_mb=self.config.max_memory_mb,\n            
max_connections=self.config.max_connections\n        )\n        \n        # 
Running flag\n        self._running = False\n    \n    async def 
initialize(self):\n        """Initialize the server."""\n        # Initialize 
connection pool\n        db_path = os.path.expanduser(self.config.db_path)\n    
self.pool = AsyncConnectionPool(db_path, 
max_connections=self.config.max_workers)\n        await self.pool.initialize()\n
\n        # Initialize database\n        from cortex.migrations import 
run_migrations\n        async with self.pool.acquire() as conn:\n            
loop = asyncio.get_event_loop()\n            await 
loop.run_in_executor(self.executor, run_migrations, conn)\n        \n        
self._running = True\n        logger.info("Edge MCP server initialized")\n    \n
async def cortex_store(\n        self,\n        project: str,\n        content: 
str,\n        fact_type: str = "knowledge",\n        tags: str = "[]",\n        
source: str = "",\n        batch: bool = False\n    ) -> dict:\n        """\n   
Store a fact (or batch of facts) in CORTEX with optimizations.\n        """\n   
from cortex.engine import CortexEngine\n        \n        start = time.time()\n 
\n        async with self.pool.acquire() as conn:\n            engine = 
CortexEngine(self.config.db_path, auto_embed=False)\n            engine._conn = 
conn\n            \n            try:\n                if batch:\n               
facts = json.loads(content)\n                    loop = 
asyncio.get_event_loop()\n                    ids = await 
loop.run_in_executor(\n                        self.executor,\n                 
engine.store_many,\n                        facts\n                    )\n      
result = {\n                        "success": True,\n                        
"fact_ids": ids,\n                        "count": len(ids)\n                   
}\n                else:\n                    parsed_tags = json.loads(tags) if 
tags else []\n                    loop = asyncio.get_event_loop()\n             
fact_id = await loop.run_in_executor(\n                        self.executor,\n 
engine.store,\n                        project,\n                        
content,\n                        fact_type,\n                        
parsed_tags,\n                        "stated",\n                        source 
or None,\n                        None,\n                        None\n         
)\n                    result = {\n                        "success": True,\n   
"fact_id": fact_id\n                    }\n                \n                # 
Invalidate cache\n                await 
self.cache.invalidate(f"search:{project}")\n                await 
self.cache.invalidate(f"recall:{project}")\n                \n                
duration_ms = (time.time() - start) * 1000\n                
self.metrics.record_request("cortex_store", duration_ms)\n                \n    
return result\n                \n            except Exception as e:\n           
self.metrics.record_error()\n                logger.error("Error in 
cortex_store: %s", e)\n                raise\n    \n    async def 
cortex_search(\n        self,\n        query: str,\n        project: str = "",\n
top_k: int = 5,\n        as_of: str = "",\n        use_cache: bool = True\n    )
-> dict:\n        """Search CORTEX with multi-tier caching."""\n        from 
cortex.engine import CortexEngine\n        \n        cache_key = 
self.cache._key(\n            "search",\n            query=query,\n            
project=project,\n            top_k=top_k,\n            as_of=as_of\n        )\n
\n        # Check cache\n        if use_cache:\n            cached = await 
self.cache.get(cache_key)\n            if cached is not None:\n                
self.metrics.record_request("cortex_search", 0, cached=True)\n                
return cached\n        \n        # Execute search\n        start = time.time()\n
\n        async def _do_search():\n            async with self.pool.acquire() as
conn:\n                engine = CortexEngine(self.config.db_path, 
auto_embed=False)\n                engine._conn = conn\n                \n      
loop = asyncio.get_event_loop()\n                results = await 
loop.run_in_executor(\n                    self.executor,\n                    
engine.search,\n                    query,\n                    project or 
None,\n                    top_k,\n                    as_of or None\n          
)\n                \n                return [\n                    {\n          
"fact_id": r.fact_id,\n                        "project": r.project,\n          
"content": r.content[:200] + "..." if len(r.content) > 200 else r.content,\n    
"score": r.score,\n                        "consensus_score": getattr(r, 
\'consensus_score\', 1.0)\n                    }\n                    for r in 
results\n                ]\n        \n        # Use circuit breaker\n        
results = await self.circuit.call(_do_search)\n        \n        result = {\n   
"results": results,\n            "count": len(results),\n            "query": 
query\n        }\n        \n        # Cache result\n        if use_cache:\n     
await self.cache.set(cache_key, result)\n        \n        duration_ms = 
(time.time() - start) * 1000\n        
self.metrics.record_request("cortex_search", duration_ms)\n        \n        
return result\n    \n    async def get_metrics(self) -> dict:\n        """Return
server metrics."""\n        return {\n            
**self.metrics.get_summary(),\n            **self.resources.get_stats()\n       
}\n    \n    async def health_check(self) -> dict:\n        """Health check 
endpoint."""\n        healthy = self.resources.check_memory()\n        \n       
try:\n            async with self.pool.acquire() as conn:\n                
conn.execute("SELECT 1")\n            db_status = "connected"\n        except 
Exception as e:\n            db_status = f"error: {e}"\n        \n        return
{\n            "status": "healthy" if healthy else "unhealthy",\n            
"database": db_status,\n            "circuit_state": self.circuit.state.value,\n
"resources": self.resources.get_stats()\n        }\n    \n    async def 
close(self):\n        """Shutdown the server."""\n        self._running = 
False\n        if self.pool:\n            await self.pool.close()\n        
self.executor.shutdown(wait=True)\n\n\n# Entry point\nif __name__ == 
"__main__":\n    import sys\n    \n    config = EdgeMCPConfig(\n        
db_path=os.environ.get("CORTEX_DB", "~/.cortex/cortex.db"),\n        
transport="stdio"\n    )\n    \n    server = EdgeMCPServer(config)\n    
asyncio.run(server.initialize())\n```\n\n### 3.5 Performance Targets\n\n| Metric
| Current | Target | Speedup |\n|--------|---------|--------|---------|\n| Cold 
search | 50ms | 50ms | — |\n| Warm search | 50ms | 1ms | **50x** |\n| Batch 
store (100) | 2300ms | 450ms | **5x** |\n| Throughput | 100 req/s | 1000 req/s |
**10x** |\n| Memory usage | Unbounded | <256MB | **Bounded** |\n| P99 latency | 
Variable | <10ms | **Consistent** |\n\n---\n\n## 4. Deployment Patterns\n\n### 
4.1 Docker Deployment\n\n```dockerfile\n# Dockerfile.edge\nFROM 
python:3.12-slim\n\n# Install system dependencies\nRUN apt-get update && apt-get
install -y \\\n    libsqlite3-dev \\\n    && rm -rf /var/lib/apt/lists/*\n\n# 
Set working directory\nWORKDIR /app\n\n# Install Python dependencies\nCOPY 
pyproject.toml .\nRUN pip install --no-cache-dir -e ".[edge]"\n\n# Copy 
application\nCOPY cortex/ ./cortex/\n\n# Create non-root user\nRUN useradd -m -u
1000 cortex && \\\n    mkdir -p /data && \\\n    chown -R cortex:cortex 
/data\n\n# Environment\nENV CORTEX_DB=/data/cortex.db\nENV 
CORTEX_MAX_MEMORY_MB=256\nENV PYTHONUNBUFFERED=1\n\nUSER cortex\n\n# Expose 
ports\nEXPOSE 8484 9999\n\n# Health check\nHEALTHCHECK --interval=30s 
--timeout=5s --start-period=5s --retries=3 \\\n    CMD python -c "import 
requests; requests.get(\'http://localhost:8484/health\')" || exit 1\n\n# 
Default: run edge-optimized MCP server\nCMD ["python", "-m", 
"cortex.mcp_server_edge"]\n```\n\n### 4.2 Kubernetes Deployment\n\n```yaml\n# 
deploy/k8s-edge-deployment.yaml\napiVersion: apps/v1\nkind: 
Deployment\nmetadata:\n  name: cortex-edge\n  labels:\n    app: 
cortex-edge\nspec:\n  replicas: 3\n  selector:\n    matchLabels:\n      app: 
cortex-edge\n  template:\n    metadata:\n      labels:\n        app: 
cortex-edge\n    spec:\n      containers:\n      - name: cortex\n        image: 
cortex:v5.0.0-edge\n        ports:\n        - containerPort: 8484\n          
name: api\n        - containerPort: 9999\n          name: mcp\n        env:\n   
- name: CORTEX_DB\n          value: "/data/cortex.db"\n        - name: 
CORTEX_MAX_MEMORY_MB\n          value: "256"\n        - name: CORTEX_CACHE_TTL\n
value: "300"\n        resources:\n          limits:\n            memory: 
"256Mi"\n            cpu: "1000m"\n          requests:\n            memory: 
"128Mi"\n            cpu: "250m"\n        volumeMounts:\n        - name: data\n 
mountPath: /data\n        livenessProbe:\n          httpGet:\n            path: 
/health\n            port: 8484\n          initialDelaySeconds: 10\n          
periodSeconds: 30\n        readinessProbe:\n          httpGet:\n            
path: /health\n            port: 8484\n          initialDelaySeconds: 5\n       
periodSeconds: 5\n      volumes:\n      - name: data\n        emptyDir: 
{}\n---\napiVersion: v1\nkind: Service\nmetadata:\n  name: cortex-edge\nspec:\n 
selector:\n    app: cortex-edge\n  ports:\n  - port: 8484\n    targetPort: 
8484\n    name: api\n  - port: 9999\n    targetPort: 9999\n    name: mcp\n  
type: ClusterIP\n```\n\n### 4.3 Edge Device Deployment (IoT/ARM)\n\n```yaml\n# 
docker-compose.edge.yml\nversion: "3.8"\n\nservices:\n  cortex-edge:\n    
build:\n      context: .\n      dockerfile: Dockerfile.edge\n      platforms:\n 
- linux/arm64\n        - linux/arm/v7\n    ports:\n      - "8484:8484"\n      - 
"9999:9999"\n    volumes:\n      - ./data:/data\n    environment:\n      - 
CORTEX_DB=/data/cortex.db\n      - CORTEX_MAX_MEMORY_MB=128\n      - 
CORTEX_QUERY_CACHE_SIZE=500\n      - CORTEX_BATCH_SIZE=50\n    restart: 
unless-stopped\n    deploy:\n      resources:\n        limits:\n          
memory: 128M\n          cpus: \'0.5\'\n```\n\n---\n\n## 5. Migration Plan\n\n###
5.1 Wave 5 Timeline\n\n```\nWeek 1-2: Immutable Vote Ledger\n├── Migration 010: 
Vote ledger schema\n├── Implementation: VoteLedger class\n├── Integration: Hook 
into vote() method\n├── CLI: vote-ledger commands\n└── Tests: 95% 
coverage\n\nWeek 3-4: HA Synchronization\n├── Migration 011: HA schema (nodes, 
vector clocks, sync log)\n├── Implementation: HASyncManager class\n├── 
Implementation: Raft consensus\n├── Implementation: CRDT merge strategies\n└── 
Tests: Multi-node simulation\n\nWeek 5-6: Edge MCP Optimization\n├── 
mcp_server_edge.py implementation\n├── Multi-tier caching\n├── Request 
batching\n├── Circuit breaker\n├── Resource monitoring\n└── Benchmark 
suite\n\nWeek 7: Deployment\n├── Dockerfile.edge\n├── 
docker-compose.edge.yml\n├── Kubernetes manifests\n├── ARM/IoT builds\n└── 
Documentation\n\nWeek 8: Integration & Testing\n├── End-to-end HA tests\n├── 
Performance validation\n├── Edge deployment tests\n├── Security audit\n└── 
Release candidate\n```\n\n### 5.2 Migration Commands\n\n```bash\n# Upgrade to 
Wave 5\ncortex migrate\n\n# Initialize vote ledger\ncortex vote-ledger init\n\n#
Create first Merkle checkpoint\ncortex vote-ledger checkpoint\n\n# Verify 
integrity\ncortex vote-ledger verify\n\n# Join HA cluster\ncortex cluster join 
--node-id node2 --peers node1:8484\n\n# Start edge-optimized MCP server\ncortex 
mcp start --transport sse --port 9999 --edge-mode\n\n# Run benchmarks\ncortex 
benchmark --suite edge\n```\n\n---\n\n## 6. Success Criteria\n\n### 6.1 
Technical Metrics\n\n| Metric | Target | Measurement 
|\n|--------|--------|-------------|\n| Vote Ledger Verification | <100ms for 
10k votes | `cortex vote-ledger verify` |\n| HA Failover Time | <5 seconds | 
Simulated node failure |\n| Data Consistency | 100% | Multi-node write/read test
|\n| MCP Cold Query | <50ms | Benchmark suite |\n| MCP Warm Query | <1ms | 
Benchmark suite |\n| MCP Throughput | >1000 req/s | Load test |\n| Cache Hit 
Rate | >80% | Runtime metrics |\n| Memory Usage | <256MB | Container metrics 
|\n| Edge Boot Time | <3 seconds | Cold start measurement |\n\n### 6.2 Adoption 
Metrics\n\n| Metric | Target |\n|--------|--------|\n| API uptime | 99.9% |\n| 
Error rate | <0.1% |\n| Mean recovery time | <5 minutes |\n| Vote tamper 
detection | 100% |\n| Consensus consistency | 99.99% |\n\n---\n\n## 7. Security 
Considerations\n\n### 7.1 Threat Model\n\n| Threat | Mitigation 
|\n|--------|------------|\n| Vote tampering | Immutable ledger with Merkle 
trees |\n| Node compromise | Raft consensus requires majority |\n| Network 
partition | CRDT merge strategies |\n| Replay attacks | Vector clocks + 
timestamps |\n| Sybil attacks | Reputation-weighted consensus (Wave 4) |\n| DoS 
| Circuit breaker + rate limiting |\n\n### 7.2 Audit Requirements\n\n- All votes
cryptographically chained\n- Merkle roots for batch verification\n- Exportable 
audit logs\n- External anchoring support (optional)\n- Tamper detection 
alerts\n\n---\n\n## Appendix A: API Changes\n\n### New Endpoints\n\n```\nPOST   
/v1/vote-ledger/checkpoint      # Create Merkle checkpoint\nGET    
/v1/vote-ledger/verify          # Verify vote ledger integrity\nPOST   
/v1/vote-ledger/export          # Export verifiable vote log\nGET    
/v1/vote-ledger/history/{fact_id} # Get vote history for fact\n\nPOST   
/v1/cluster/join                # Join HA cluster\nPOST   /v1/cluster/leave     
# Leave HA cluster\nGET    /v1/cluster/status              # Get cluster 
status\nGET    /v1/cluster/nodes               # List cluster nodes\n\nGET    
/v1/edge/metrics                # Edge server metrics\nGET    /v1/edge/health   
# Edge health check\nPOST   /v1/edge/cache/invalidate       # Invalidate 
cache\n```\n\n### New CLI Commands\n\n```\ncortex vote-ledger checkpoint        
# Create checkpoint\ncortex vote-ledger verify              # Verify 
integrity\ncortex vote-ledger export              # Export log\ncortex 
vote-ledger history <fact_id>   # Get vote history\n\ncortex cluster join       
# Join cluster\ncortex cluster leave                   # Leave cluster\ncortex 
cluster status                  # Show cluster status\ncortex cluster nodes     
# List nodes\n\ncortex mcp start --edge-mode           # Start edge MCP 
server\ncortex benchmark --suite edge          # Run edge 
benchmarks\n```\n\n---\n\n**End of Wave 5 Proposal**\n\n*Prepared for CORTEX 
V4.0 Architecture Review | 2026-02-16*'
            )
        ],
        extras=None
    )
)
StepBegin(n=6)
ToolCall(
    type='function',
    id='tool_JmMxydcoX467neY8tuv00IZp',
    function=FunctionBody(
        name='SetTodoList',
        arguments='{"todos": [{"title": "Analyze current architecture and 
consensus layer", "status": "done"}, {"title": "Design Wave 5: Immutable Vote 
Logging", "status": "done"}, {"title": "Design Wave 5: HA Ledger 
Synchronization", "status": "done"}, {"title": "Design Wave 5: MCP Server Edge 
Optimization", "status": "done"}, {"title": "Create comprehensive Wave 5 
proposal document", "status": "done"}]}'
    ),
    extras=None
)
ToolResult(
    tool_call_id='tool_JmMxydcoX467neY8tuv00IZp',
    return_value=ToolReturnValue(
        is_error=False,
        output='',
        message='Todo list updated',
        display=[
            TodoDisplayBlock(
                type='todo',
                items=[
                    TodoDisplayItem(
                        title='Analyze current architecture and consensus 
layer',
                        status='done'
                    ),
                    TodoDisplayItem(
                        title='Design Wave 5: Immutable Vote Logging',
                        status='done'
                    ),
                    TodoDisplayItem(
                        title='Design Wave 5: HA Ledger Synchronization',
                        status='done'
                    ),
                    TodoDisplayItem(
                        title='Design Wave 5: MCP Server Edge Optimization',
                        status='done'
                    ),
                    TodoDisplayItem(
                        title='Create comprehensive Wave 5 proposal document',
                        status='done'
                    )
                ]
            )
        ],
        extras=None
    )
)
StatusUpdate(
    context_usage=0.279998779296875,
    token_usage=TokenUsage(
        input_other=68536,
        output=112,
        input_cache_read=4864,
        input_cache_creation=0
    ),
    message_id='chatcmpl-bq4btRjD1vGyHLc6LkvvUPbS'
)
StepBegin(n=7)
TextPart(
    type='text',
    text='Now let me create a summary analysis document that ties everything 
together:'
)
ToolCall(
    type='function',
    id='tool_lzsdwwVMfAmeChfYo3qfgVqR',
    function=FunctionBody(
        name='WriteFile',
        arguments='{"path": 
"/Users/borjafernandezangulo/cortex/WAVE5_ARCHITECTURE_ANALYSIS.md", "content": 
"# CORTEX V4.0 — Wave 5 Architecture Analysis\\n## Executive Summary: 
Persistence & Deployment\\n\\n**Date:** 2026-02-16  \\n**Status:** Technical 
Design Complete  \\n**Classification:** Strategic Architecture Document  
\\n\\n---\\n\\n## 1. Current State Analysis\\n\\n### 1.1 CORTEX V4.0 
Architecture 
Overview\\n\\n```\\n┌───────────────────────────────────────────────────────────
──────────────────┐\\n│                        CORTEX V4.0 ARCHITECTURE         
│\\n├───────────────────────────────────────────────────────────────────────────
──┤\\n│                                                                         
     │\\n│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐
│\\n│  │     CLI      │  │  REST API    │  │  Dashboard   │  │   MCP      │     
│\\n│  │  (cortex)    │  │  (FastAPI)   │  │  (Noir UI)   │  │  Server    │     
│\\n│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘     
│\\n│         │                 │                 │                │            
│\\n│         └─────────────────┴─────────────────┴────────────────┘            
│\\n│                                   │                                       
│\\n│                                   ▼                                       
│\\n│                    ┌─────────────────────────────┐                        
│\\n│                    │      Core Engine Layer      │                        
│\\n│                    │  ┌─────────────────────┐    │                        
│\\n│                    │  │   CortexEngine      │    │                        
│\\n│                    │  │  - Facts (CRUD)     │    │                        
│\\n│                    │  │  - Search (semantic)│    │                        
│\\n│                    │  │  - Temporal queries │    │                        
│\\n│                    │  │  - Graph memory     │    │                        
│\\n│                    │  └─────────────────────┘    │                        
│\\n│                    │  ┌─────────────────────┐    │                        
│\\n│                    │  │  Consensus Layer    │◄───┼─── Wave 4              
│\\n│                    │  │  - Vote casting     │    │                        
│\\n│                    │  │  - Score tracking   │    │                        
│\\n│                    │  │  - Reputation (RWC) │    │                        
│\\n│                    │  └─────────────────────┘    │                        
│\\n│                    └──────────────┬──────────────┘                        
│\\n│                                   │                                       
│\\n│         ┌─────────────────────────┼─────────────────────────┐             
│\\n│         │                         │                         │             
│\\n│         ▼                         ▼                         ▼             
│\\n│  ┌──────────────┐      ┌──────────────────┐      ┌──────────────┐         
│\\n│  │   SQLite     │      │   sqlite-vec     │      │   Ledger     │         
│\\n│  │  (Facts)     │      │ (Vector Search)  │      │ (Hash Chain) │         
│\\n│  └──────────────┘      └──────────────────┘      └──────────────┘         
│\\n│                                                                           
│\\n└───────────────────────────────────────────────────────────────────────────
──┘\\n```\\n\\n### 1.2 Wave 4 Consensus Layer (Current)\\n\\n**Neural Swarm 
Consensus** provides distributed fact verification with:\\n\\n| Component | 
Implementation | Status |\\n|-----------|---------------|--------|\\n| Base 
Consensus (v1) | Linear scoring: `score = 1.0 + Σ(vote) × 0.1` | ✅ Active |\\n|
RWC Schema (v2) | Agent registry, reputation-weighted votes | ✅ Schema Ready 
|\\n| Vote API | `/facts/{id}/vote` endpoint | ✅ Implemented |\\n| Vote Storage
| `consensus_votes` and `consensus_votes_v2` tables | ✅ Implemented 
|\\n\\n**Current Vulnerabilities:**\\n1. **No cryptographic vote integrity** — 
Votes can be modified by database admins\\n2. **No audit trail** — No external 
verifiability of vote history\\n3. **Single point of failure** — No replication 
or failover\\n4. **Limited MCP performance** — Blocking operations, no 
caching\\n\\n---\\n\\n## 2. Wave 5: Three-Pillar Architecture\\n\\n### 2.1 
Pillar 1: Immutable Vote Logging\\n\\n**Problem:** Current votes are stored in 
standard SQL tables without cryptographic protection.\\n\\n**Solution:** 
Hash-chained vote ledger with Merkle 
trees\\n\\n```\\n┌──────────────────────────────────────────────────────────────
───────────────┐\\n│                    IMMUTABLE VOTE LEDGER                   
│\\n├───────────────────────────────────────────────────────────────────────────
──┤\\n│                                                                         
     │\\n│   Genesis    Vote 1      Vote 2      Vote 3      Vote N              
│\\n│   ┌─────┐   ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐                      
│\\n│   │ 0x0 │◄──┤ h1  │◄───┤ h2  │◄───┤ h3  │◄───┤ hN  │  ← Hash Chain        
│\\n│   └─────┘   └──┬──┘    └──┬──┘    └──┬──┘    └──┬──┘                      
│\\n│                │          │          │          │                         
│\\n│                ▼          ▼          ▼          ▼                         
│\\n│              ┌─────────────────────────────────────┐                      
│\\n│              │         Merkle Tree Root            │  ← Batch Proof       
│\\n│              │            (every 1k votes)         │                      
│\\n│              └─────────────────────────────────────┘                      
│\\n│                              │                                            
│\\n│                              ▼                                            
│\\n│              ┌─────────────────────────────────────┐                      
│\\n│              │      External Signature (opt)       │  ← Tamper Proof      
│\\n│              └─────────────────────────────────────┘                      
│\\n│                                                                           
│\\n└───────────────────────────────────────────────────────────────────────────
──┘\\n```\\n\\n**Key Features:**\\n- Each vote includes `prev_hash` forming an 
immutable chain\\n- Merkle roots every 1,000 votes for efficient 
verification\\n- Exportable audit logs with integrity proofs\\n- Tamper 
detection via hash verification\\n\\n**Schema Additions:**\\n```sql\\nCREATE 
TABLE vote_ledger (\\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\\n    fact_id 
INTEGER NOT NULL,\\n    agent_id TEXT NOT NULL,\\n    vote INTEGER NOT NULL,\\n 
vote_weight REAL NOT NULL,\\n    prev_hash TEXT NOT NULL,      -- Previous entry
hash\\n    hash TEXT NOT NULL,           -- SHA-256 of this entry\\n    
timestamp TEXT NOT NULL,\\n    signature TEXT                -- Optional Ed25519
signature\\n);\\n\\nCREATE TABLE vote_merkle_roots (\\n    id INTEGER PRIMARY 
KEY AUTOINCREMENT,\\n    root_hash TEXT NOT NULL,\\n    vote_start_id INTEGER 
NOT NULL,\\n    vote_end_id INTEGER NOT NULL,\\n    vote_count INTEGER NOT 
NULL\\n);\\n```\\n\\n---\\n\\n### 2.2 Pillar 2: High-Availability 
Synchronization\\n\\n**Problem:** Single-node deployment with no failover 
capability.\\n\\n**Solution:** Raft consensus + CRDT-based 
replication\\n\\n```\\n┌────────────────────────────────────────────────────────
─────────────────────┐\\n│                    HA CORTEX CLUSTER                 
│\\n├───────────────────────────────────────────────────────────────────────────
──┤\\n│                                                                         
     │\\n│   
┌───────────────────────────────────────────────────────────────────┐    │\\n│  
│                    CONSENSUS LAYER (Raft)                          │    │\\n│ 
│                                                                    │    │\\n│ 
│    ┌─────────┐      ┌─────────┐      ┌─────────┐                  │    │\\n│  
│    │ Node 1  │◄────►│ Node 2  │◄────►│ Node 3  │                  │    │\\n│  
│    │ LEADER  │      │FOLLOWER │      │FOLLOWER │                  │    │\\n│  
│    └────┬────┘      └────┬────┘      └────┬────┘                  │    │\\n│  
│         │                │                │                        │    │\\n│ 
│         └────────────────┴────────────────┘                        │    │\\n│ 
│                      │                                             │    │\\n│ 
│                      ▼                                             │    │\\n│ 
│         ┌─────────────────────────┐                                │    │\\n│ 
│         │   Log Replication       │  ← Strong Consistency          │    │\\n│ 
│         │   (Majority Ack)        │                                │    │\\n│ 
│         └─────────────────────────┘                                │    │\\n│ 
└───────────────────────────────────────────────────────────────────┘    │\\n│  
│                                         │\\n│                                 
▼                                         │\\n│   
┌───────────────────────────────────────────────────────────────────┐    │\\n│  
│                    DATA LAYER (CRDT)                               │    │\\n│ 
│                                                                    │    │\\n│ 
│  Facts:     LWW (Last-Write-Wins) Register                        │    │\\n│  
│  Votes:     OR-Set (Observed-Remove Set)                          │    │\\n│  
│  Agents:    LWW Register with vector clock merge                  │    │\\n│  
│                                                                    │    │\\n│ 
│  Sync: Anti-entropy gossip every 30s                              │    │\\n│  
└───────────────────────────────────────────────────────────────────┘    │\\n│  
│\\n└───────────────────────────────────────────────────────────────────────────
──┘\\n```\\n\\n**Key Features:**\\n- **Raft Consensus:** Leader election, log 
replication, automatic failover\\n- **CRDT Data Types:** Conflict-free 
replicated data types for automatic merge\\n- **Vector Clocks:** Causality 
tracking for concurrent updates\\n- **Merkle Trees:** Efficient diff for 
synchronization\\n- **Anti-Entropy Gossip:** Epidemic broadcast for eventual 
consistency\\n\\n**Consistency Model:**\\n| Operation | Consistency | Mechanism 
|\\n|-----------|-------------|-----------|\\n| Vote casting | Strong | Raft 
consensus (majority ack) |\\n| Fact reads | Eventual | CRDT with anti-entropy 
|\\n| Agent updates | Eventual | LWW with vector clocks |\\n| Ledger queries | 
Strong | Routed to leader |\\n\\n---\\n\\n### 2.3 Pillar 3: Edge-Optimized MCP 
Server\\n\\n**Problem:** Current MCP server is single-threaded with no caching 
or resource limits.\\n\\n**Solution:** Async multi-transport server with 
multi-tier 
caching\\n\\n```\\n┌────────────────────────────────────────────────────────────
─────────────────┐\\n│                    EDGE-OPTIMIZED MCP SERVER             
│\\n├───────────────────────────────────────────────────────────────────────────
──┤\\n│                                                                         
     │\\n│  
┌─────────────────────────────────────────────────────────────────────┐   │\\n│ 
│  Transport Layer: stdio | SSE | WebSocket | HTTP/2                  │   │\\n│ 
└────────────────────────────────┬────────────────────────────────────┘   │\\n│ 
│                                         │\\n│  
┌────────────────────────────────▼────────────────────────────────────┐   │\\n│ 
│  Optimization Layer                                                 │   │\\n│ 
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐       │   │\\n│  
│  │ Multi-Tier   │  │   Request    │  │   Circuit Breaker   │       │   │\\n│  
│  │ Cache        │  │   Batching   │  │   (Fault Tolerance) │       │   │\\n│  
│  │ ┌──────────┐ │  │              │  │                     │       │   │\\n│  
│  │ │ L1: LRU  │ │  │ Flush: 10ms  │  │ Failure: 5          │       │   │\\n│  
│  │ │ L2: Redis│ │  │ Max: 100 ops │  │ Timeout: 30s        │       │   │\\n│  
│  │ └──────────┘ │  │              │  │ Cooldown: 5s        │       │   │\\n│  
│  └──────────────┘  └──────────────┘  └─────────────────────┘       │   │\\n│  
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐       │   │\\n│  
│  │ Connection   │  │   Resource   │  │     Metrics         │       │   │\\n│  
│  │ Pool (5)     │  │    Limits    │  │   (Prometheus)      │       │   │\\n│  
│  │              │  │              │  │                     │       │   │\\n│  
│  │ WAL mode     │  │ Memory: 256MB│  │ Latency P99         │       │   │\\n│  
│  │ Async I/O    │  │ CPU: 1 core  │  │ Cache hit rate      │       │   │\\n│  
│  └──────────────┘  └──────────────┘  └─────────────────────┘       │   │\\n│  
└────────────────────────────────────────────────────────────────────┘   │\\n│  
│\\n└───────────────────────────────────────────────────────────────────────────
──┘\\n```\\n\\n**Key Features:**\\n- **Multi-Transport:** stdio (default), SSE, 
WebSocket, HTTP/2\\n- **Multi-Tier Cache:** L1 in-memory LRU, L2 Redis 
(optional)\\n- **Request Batching:** Automatic batching of writes (10ms flush, 
100 ops max)\\n- **Circuit Breaker:** Fault tolerance with automatic 
recovery\\n- **Resource Monitoring:** Memory/CPU limits with graceful 
degradation\\n- **Connection Pooling:** Async SQLite connection pool (WAL 
mode)\\n\\n**Performance Targets:**\\n| Metric | Current | Target | Improvement 
|\\n|--------|---------|--------|-------------|\\n| Warm search | 50ms | 1ms | 
**50x** |\\n| Batch store (100) | 2300ms | 450ms | **5x** |\\n| Throughput | 100
req/s | 1000 req/s | **10x** |\\n| Memory usage | Unbounded | <256MB | 
**Bounded** |\\n| P99 latency | Variable | <10ms | **Consistent** 
|\\n\\n---\\n\\n## 3. Integration Architecture\\n\\n### 3.1 How the Three 
Pillars Work 
Together\\n\\n```\\n┌───────────────────────────────────────────────────────────
──────────────────┐\\n│                    WAVE 5 INTEGRATED ARCHITECTURE       
│\\n├───────────────────────────────────────────────────────────────────────────
──┤\\n│                                                                         
     │\\n│  
┌─────────────────────────────────────────────────────────────────────┐   │\\n│ 
│                         CLIENT LAYER                                 │   │\\n│
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │   │\\n│ 
│  │  CLI Client  │  │  REST Client │  │    MCP Client (Edge)     │   │   │\\n│ 
│  └──────┬───────┘  └──────┬───────┘  └───────────┬──────────────┘   │   │\\n│ 
│         │                 │                      │                  │   │\\n│ 
└─────────┼─────────────────┼──────────────────────┼──────────────────┘   │\\n│ 
│                 │                      │                       │\\n│          
▼                 ▼                      ▼                       │\\n│  
┌─────────────────────────────────────────────────────────────────────┐   │\\n│ 
│                      CORTEX CLUSTER (3+ nodes)                       │   │\\n│
│                                                                      │   │\\n│
│  ┌───────────────────────────────────────────────────────────────┐  │   │\\n│ 
│  │              PILLAR 2: HA SYNCHRONIZATION                      │  │   │\\n│
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐                       │  │   │\\n│  
│  │  │ Node 1  │◄►│ Node 2  │◄►│ Node 3  │  ← Raft + CRDT        │  │   │\\n│  
│  │  │ (Leader)│  │(Follower)│  │(Follower)│                      │  │   │\\n│ 
│  │  └────┬────┘  └────┬────┘  └────┬────┘                       │  │   │\\n│  
│  │       └─────────────┴─────────────┘                            │  │   │\\n│
│  │                    │                                           │  │   │\\n│
│  └────────────────────┼───────────────────────────────────────────┘  │   │\\n│
│                       │                                              │   │\\n│
│  ┌────────────────────▼───────────────────────────────────────────┐  │   │\\n│
│  │              PILLAR 1: IMMUTABLE VOTE LEDGER                    │  │   
│\\n│  │  │                                                                 │  │
│\\n│  │  │  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │  │ 
│\\n│  │  │  │ Vote Cast    │────►│ Hash Chain   │────►│ Merkle Root  │    │  │ 
│\\n│  │  │  │ (Event)      │     │ (SHA-256)    │     │ (Batch)      │    │  │ 
│\\n│  │  │  └──────────────┘     └──────────────┘     └──────────────┘    │  │ 
│\\n│  │  │                                                                 │  │
│\\n│  │  │  Every vote is:                                                   │ 
│   │\\n│  │  │  1. Appended to hash-chained ledger                             
│  │   │\\n│  │  │  2. Replicated via Raft (strong consistency)                 
│  │   │\\n│  │  │  3. Periodically batched into Merkle tree                    
│  │   │\\n│  │  │                                                              
│  │   │\\n│  │  
└─────────────────────────────────────────────────────────────────┘  │   │\\n│  
│                                                                       │   
│\\n│  └───────────────────────────────────────────────────────────────────────┘
│\\n│                                                                           
│\\n│  ┌─────────────────────────────────────────────────────────────────────┐  
│\\n│  │              PILLAR 3: EDGE MCP SERVER (Per-Node)                    │ 
│\\n│  │                                                                      │ 
│\\n│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐        │  
│\\n│  │  │ Multi-Transport│  │ Multi-Tier   │  │   Resource          │        │
│\\n│  │  │ (stdio/SSE/   │  │ Cache        │  │   Monitoring        │        │ 
│\\n│  │  │  WebSocket)   │  │ (L1/L2)      │  │   (256MB limit)     │        │ 
│\\n│  │  └──────────────┘  └──────────────┘  └─────────────────────┘        │  
│\\n│  │                                                                      │ 
│\\n│  │  Each node runs edge-optimized MCP server for local queries          │ 
│\\n│  │                                                                      │ 
│\\n│  └─────────────────────────────────────────────────────────────────────┘  
│\\n│                                                                           
│\\n└───────────────────────────────────────────────────────────────────────────
──┘\\n```\\n\\n### 3.2 Data Flow: Casting a Vote\\n\\n```\\n1. Client sends vote
request to MCP server\\n        │\\n        ▼\\n2. Edge MCP server receives 
request\\n   ├── Check circuit breaker\\n   ├── Acquire connection from pool\\n 
└── Forward to local engine\\n        │\\n        ▼\\n3. Local engine processes 
vote\\n   ├── Verify agent reputation\\n   ├── Record vote in 
consensus_votes_v2\\n   ├── Append to vote_ledger (hash chain)\\n   └── 
Recalculate consensus score\\n        │\\n        ▼\\n4. HA Sync replicates vote
(if leader)\\n   ├── Append to Raft log\\n   ├── Replicate to followers\\n   └──
Wait for majority ack\\n        │\\n        ▼\\n5. Followers apply vote\\n   ├──
Update local consensus_votes_v2\\n   ├── Append to local vote_ledger\\n   └── 
Update Merkle tree\\n        │\\n        ▼\\n6. Response returned to client\\n  
├── Vote confirmed\\n   ├── New consensus score\\n   └── Ledger entry 
hash\\n```\\n\\n---\\n\\n## 4. Deployment Topologies\\n\\n### 4.1 Single-Node 
(Development)\\n\\n```\\n┌─────────────────────────────────────────┐\\n│        
Development Workstation       │\\n│                                         
│\\n│  ┌─────────────────────────────────┐   │\\n│  │  CORTEX Single Node       
│   │\\n│  │                                 │   │\\n│  │  ┌──────────┐  
┌──────────┐    │   │\\n│  │  │   API    │  │   MCP    │    │   │\\n│  │  │  
Server  │  │  Server  │    │   │\\n│  │  └────┬─────┘  └────┬─────┘    │   │\\n│
│       └─────────────┘          │   │\\n│  │              │                  │ 
│\\n│  │       ┌──────▼──────┐           │   │\\n│  │       │   SQLite    │     
│   │\\n│  │       │  (Single)   │           │   │\\n│  │       └─────────────┘ 
│   │\\n│  │                                 │   │\\n│  
└─────────────────────────────────┘   │\\n│                                     
│\\n└─────────────────────────────────────────┘\\n```\\n\\n### 4.2 Three-Node HA
Cluster 
(Production)\\n\\n```\\n┌───────────────────────────────────────────────────────
──────────────────────┐\\n│                         Production Cluster          
│\\n├───────────────────────────────────────────────────────────────────────────
──┤\\n│                                                                         
     │\\n│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐    
│\\n│  │     Node 1       │  │     Node 2       │  │     Node 3       │         
│\\n│  │    (Leader)      │  │   (Follower)     │  │   (Follower)     │         
│\\n│  │                  │  │                  │  │                  │         
│\\n│  │  ┌────────────┐  │  │  ┌────────────┐  │  │  ┌────────────┐  │         
│\\n│  │  │ API Server │  │  │  │ API Server │  │  │  │ API Server │  │         
│\\n│  │  │  (Primary) │  │  │  │ (Replica)  │  │  │  │ (Replica)  │  │         
│\\n│  │  └────────────┘  │  │  └────────────┘  │  │  └────────────┘  │         
│\\n│  │  ┌────────────┐  │  │  ┌────────────┐  │  │  ┌────────────┐  │         
│\\n│  │  │ Edge MCP   │  │  │  │ Edge MCP   │  │  │  │ Edge MCP   │  │         
│\\n│  │  │  Server    │  │  │  │  Server    │  │  │  │  Server    │  │         
│\\n│  │  └────────────┘  │  │  └────────────┘  │  │  └────────────┘  │         
│\\n│  │  ┌────────────┐  │  │  ┌────────────┐  │  │  ┌────────────┐  │         
│\\n│  │  │   SQLite   │  │  │  │   SQLite   │  │  │  │   SQLite   │  │         
│\\n│  │  │  (Local)   │◄─┼──┼─►│  (Local)   │◄─┼──┼─►│  (Local)   │  │         
│\\n│  │  └────────────┘  │  │  └────────────┘  │  │  └────────────┘  │         
│\\n│  │                  │  │                  │  │                  │         
│\\n│  │  ┌────────────┐  │  │  ┌────────────┐  │  │  ┌────────────┐  │         
│\\n│  │  │   Raft     │◄─┼──┼─►│   Raft     │◄─┼──┼─►│   Raft     │  │         
│\\n│  │  │  (Leader)  │  │  │  │(Follower)  │  │  │  │(Follower)  │  │         
│\\n│  │  └────────────┘  │  │  └────────────┘  │  │  └────────────┘  │         
│\\n│  │                  │  │                  │  │                  │         
│\\n│  └──────────────────┘  └──────────────────┘  └──────────────────┘         
│\\n│           ▲                    ▲                    ▲                     
│\\n│           └────────────────────┴────────────────────┘                     
│\\n│                         Load Balancer                                     
│\\n│                              │                                            
│\\n│                         ┌────┴────┐                                       
│\\n│                         │ Clients │                                       
│\\n│                         └─────────┘                                       
│\\n│                                                                           
│\\n└───────────────────────────────────────────────────────────────────────────
──┘\\n```\\n\\n### 4.3 Edge Deployment 
(IoT/ARM)\\n\\n```\\n┌──────────────────────────────────────────────────────────
───────────────────┐\\n│                         Edge Deployment                
│\\n├───────────────────────────────────────────────────────────────────────────
──┤\\n│                                                                         
     │\\n│  
┌─────────────────────────────────────────────────────────────────────┐   │\\n│ 
│                    Edge Device (Raspberry Pi / ARM)                  │   │\\n│
│                                                                      │   │\\n│
│  ┌───────────────────────────────────────────────────────────────┐  │   │\\n│ 
│  │              CORTEX Edge Node                                  │  │   │\\n│
│  │                                                                │  │   │\\n│
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐  │  │   │\\n│ 
│  │  │  Edge MCP    │  │  Local Cache │  │  SQLite (WAL mode)  │  │  │   │\\n│ 
│  │  │  Server      │  │  (LRU 500)   │  │  (128MB limit)      │  │  │   │\\n│ 
│  │  │              │  │              │  │                     │  │  │   │\\n│ 
│  │  │  - stdio     │  │  - Facts     │  │  - Local facts      │  │  │   │\\n│ 
│  │  │  - SSE       │  │  - Embeddings│  │  - Local votes      │  │  │   │\\n│ 
│  │  │  (no WS)     │  │              │  │  - Sync queue       │  │  │   │\\n│ 
│  │  └──────────────┘  └──────────────┘  └─────────────────────┘  │  │   │\\n│ 
│  │                                                                │  │   │\\n│
│  │  Resource Limits:                                               │  │   
│\\n│  │  │  - Memory: 128MB                                                │  │
│\\n│  │  │  - CPU: 0.5 cores                                               │  │
│\\n│  │  │  - Storage: 1GB                                                 │  │
│\\n│  │  │                                                                │  │ 
│\\n│  │  └───────────────────────────────────────────────────────────────┘  │  
│\\n│  │                                                                      │ 
│\\n│  │  Periodic Sync (when connected):                                    │  
│\\n│  │  ┌──────────────┐         ┌──────────────┐                         │   
│\\n│  │  │  Edge Node   │◄───────►│  Hub Node    │                         │   
│\\n│  │  │  (Offline)   │  WiFi   │  (Online)    │                         │   
│\\n│  │  └──────────────┘         └──────────────┘                         │   
│\\n│  │                                                                      │ 
│\\n│  └─────────────────────────────────────────────────────────────────────┘  
│\\n│                                                                           
│\\n└───────────────────────────────────────────────────────────────────────────
──┘\\n```\\n\\n---\\n\\n## 5. Security Analysis\\n\\n### 5.1 Threat Model & 
Mitigations\\n\\n| Threat | Severity | Mitigation 
|\\n|--------|----------|------------|\\n| **Vote Tampering** | Critical | 
Immutable ledger with Merkle trees; any modification breaks hash chain |\\n| 
**Node Compromise** | High | Raft consensus requires majority; compromised node 
can\'t alter consensus |\\n| **Network Partition** | Medium | CRDT merge 
strategies; automatic conflict resolution when partition heals |\\n| **Replay 
Attacks** | Medium | Vector clocks + timestamps; duplicate votes detected and 
rejected |\\n| **Sybil Attacks** | Medium | Reputation-weighted consensus (Wave 
4); new agents have low reputation |\\n| **DoS** | Medium | Circuit breaker + 
rate limiting; graceful degradation under load |\\n| **Eavesdropping** | Low | 
TLS for inter-node communication; encrypted replication |\\n| **Data Loss** | 
Low | Multi-node replication; automatic failover; regular backups |\\n\\n### 5.2
Audit & Compliance\\n\\n**Immutable Vote Ledger provides:**\\n- Complete audit 
trail of all consensus decisions\\n- Cryptographic proof of vote ordering and 
timing\\n- Exportable logs for external auditors\\n- Tamper detection with 
automated alerts\\n- Optional external anchoring (blockchain, timestamp 
services)\\n\\n---\\n\\n## 6. Performance Projections\\n\\n### 6.1 Vote 
Processing\\n\\n| Scenario | Latency | Throughput 
|\\n|----------|---------|------------|\\n| Single-node vote | 5ms | 200 
votes/sec |\\n| HA cluster vote (leader) | 15ms | 500 votes/sec |\\n| HA cluster
vote (follower redirect) | 20ms | 400 votes/sec |\\n| Batch vote (100 votes) | 
100ms | 1000 votes/sec |\\n\\n### 6.2 Query Performance\\n\\n| Query Type | Cold
| Warm (Cached) | Improvement 
|\\n|------------|------|---------------|-------------|\\n| Semantic search | 
50ms | 1ms | **50x** |\\n| Fact recall | 10ms | 0.5ms | **20x** |\\n| Graph 
query | 30ms | 5ms | **6x** |\\n| Ledger verification | 100ms (10k entries) | 
N/A | Baseline |\\n\\n### 6.3 Resource Usage\\n\\n| Deployment | Memory | CPU | 
Storage |\\n|------------|--------|-----|---------|\\n| Single-node | 128MB | 
0.5 cores | 1GB |\\n| HA node | 256MB | 1 core | 5GB |\\n| Edge device | 128MB |
0.5 cores | 1GB |\\n\\n---\\n\\n## 7. Migration Path\\n\\n### 7.1 From Wave 4 to
Wave 5\\n\\n```\\nPhase 1: Immutable Vote Ledger (Week 1-2)\\n├── Backup 
existing database\\n├── Run migration 010 (vote_ledger schema)\\n├── Deploy 
VoteLedger class\\n├── Update vote() to append to ledger\\n└── Verify: cortex 
vote-ledger verify\\n\\nPhase 2: HA Synchronization (Week 3-4)\\n├── Deploy 
second node\\n├── Run migration 011 (HA schema)\\n├── Configure Raft 
cluster\\n├── Test failover\\n└── Verify: cortex cluster status\\n\\nPhase 3: 
Edge MCP (Week 5-6)\\n├── Deploy mcp_server_edge.py\\n├── Configure 
caching\\n├── Test performance benchmarks\\n└── Verify: cortex benchmark --suite
edge\\n\\nPhase 4: Production Cutover (Week 7-8)\\n├── Deploy third node\\n├── 
Update load balancer\\n├── Monitor metrics\\n└── Document 
runbooks\\n```\\n\\n### 7.2 Backward Compatibility\\n\\n- Wave 5 is **backward 
compatible** with Wave 4 clients\\n- Vote ledger is **append-only** — existing 
votes remain valid\\n- HA cluster can operate with **mixed versions** during 
upgrade\\n- Edge MCP server maintains **same protocol** as standard 
MCP\\n\\n---\\n\\n## 8. Conclusion\\n\\nWave 5 transforms CORTEX from a 
development-ready system into a **production-grade sovereign memory 
infrastructure**:\\n\\n1. **Immutable Vote Logging** ensures cryptographic 
integrity of all consensus decisions\\n2. **High-Availability Synchronization** 
provides automatic failover and geographic distribution\\n3. **Edge-Optimized 
MCP Server** enables deployment on resource-constrained devices\\n\\nTogether, 
these capabilities enable:\\n- **Sovereign AI deployments** with tamper-evident 
consensus\\n- **Enterprise-grade availability** with 99.9% uptime\\n- **Edge 
computing scenarios** with sub-millisecond query latency\\n\\n**Next 
Steps:**\\n1. Implement Migration 010 (Immutable Vote Ledger)\\n2. Implement 
Migration 011 (HA Synchronization)\\n3. Implement Edge MCP Server\\n4. Load 
testing with 10k requests/sec\\n5. Security audit and penetration testing\\n6. 
Documentation and deployment guides\\n\\n---\\n\\n**End of Architecture 
Analysis**\\n\\n*Prepared for CORTEX V4.0 Wave 5 Implementation | 
2026-02-16*\\n"}'
    ),
    extras=None
)
StatusUpdate(
    context_usage=0.2805290222167969,
    token_usage=TokenUsage(
        input_other=323,
        output=7826,
        input_cache_read=73216,
        input_cache_creation=0
    ),
    message_id='chatcmpl-3ZMODZUnqCaWV9ozZBnZWUvs'
)
ToolResult(
    tool_call_id='tool_lzsdwwVMfAmeChfYo3qfgVqR',
    return_value=ToolReturnValue(
        is_error=False,
        output='',
        message='File successfully overwritten. Current size: 44283 bytes.',
        display=[
            DiffDisplayBlock(
                type='diff',
                path='/Users/borjafernandezangulo/cortex/WAVE5_ARCHITECTURE_ANAL
YSIS.md',
                old_text='',
                new_text="# CORTEX V4.0 — Wave 5 Architecture Analysis\n## 
Executive Summary: Persistence & Deployment\n\n**Date:** 2026-02-16  
\n**Status:** Technical Design Complete  \n**Classification:** Strategic 
Architecture Document  \n\n---\n\n## 1. Current State Analysis\n\n### 1.1 CORTEX
V4.0 Architecture 
Overview\n\n```\n┌──────────────────────────────────────────────────────────────
───────────────┐\n│                        CORTEX V4.0 ARCHITECTURE             
│\n├────────────────────────────────────────────────────────────────────────────
─┤\n│                                                                           
   │\n│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐   
│\n│  │     CLI      │  │  REST API    │  │  Dashboard   │  │   MCP      │      
│\n│  │  (cortex)    │  │  (FastAPI)   │  │  (Noir UI)   │  │  Server    │      
│\n│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘      
│\n│         │                 │                 │                │             
│\n│         └─────────────────┴─────────────────┴────────────────┘             
│\n│                                   │                                        
│\n│                                   ▼                                        
│\n│                    ┌─────────────────────────────┐                         
│\n│                    │      Core Engine Layer      │                         
│\n│                    │  ┌─────────────────────┐    │                         
│\n│                    │  │   CortexEngine      │    │                         
│\n│                    │  │  - Facts (CRUD)     │    │                         
│\n│                    │  │  - Search (semantic)│    │                         
│\n│                    │  │  - Temporal queries │    │                         
│\n│                    │  │  - Graph memory     │    │                         
│\n│                    │  └─────────────────────┘    │                         
│\n│                    │  ┌─────────────────────┐    │                         
│\n│                    │  │  Consensus Layer    │◄───┼─── Wave 4              
│\n│                    │  │  - Vote casting     │    │                         
│\n│                    │  │  - Score tracking   │    │                         
│\n│                    │  │  - Reputation (RWC) │    │                         
│\n│                    │  └─────────────────────┘    │                         
│\n│                    └──────────────┬──────────────┘                         
│\n│                                   │                                        
│\n│         ┌─────────────────────────┼─────────────────────────┐              
│\n│         │                         │                         │              
│\n│         ▼                         ▼                         ▼              
│\n│  ┌──────────────┐      ┌──────────────────┐      ┌──────────────┐         
│\n│  │   SQLite     │      │   sqlite-vec     │      │   Ledger     │         
│\n│  │  (Facts)     │      │ (Vector Search)  │      │ (Hash Chain) │         
│\n│  └──────────────┘      └──────────────────┘      └──────────────┘         
│\n│                                                                            
│\n└────────────────────────────────────────────────────────────────────────────
─┘\n```\n\n### 1.2 Wave 4 Consensus Layer (Current)\n\n**Neural Swarm 
Consensus** provides distributed fact verification with:\n\n| Component | 
Implementation | Status |\n|-----------|---------------|--------|\n| Base 
Consensus (v1) | Linear scoring: `score = 1.0 + Σ(vote) × 0.1` | ✅ Active |\n| 
RWC Schema (v2) | Agent registry, reputation-weighted votes | ✅ Schema Ready 
|\n| Vote API | `/facts/{id}/vote` endpoint | ✅ Implemented |\n| Vote Storage |
`consensus_votes` and `consensus_votes_v2` tables | ✅ Implemented 
|\n\n**Current Vulnerabilities:**\n1. **No cryptographic vote integrity** — 
Votes can be modified by database admins\n2. **No audit trail** — No external 
verifiability of vote history\n3. **Single point of failure** — No replication 
or failover\n4. **Limited MCP performance** — Blocking operations, no 
caching\n\n---\n\n## 2. Wave 5: Three-Pillar Architecture\n\n### 2.1 Pillar 1: 
Immutable Vote Logging\n\n**Problem:** Current votes are stored in standard SQL 
tables without cryptographic protection.\n\n**Solution:** Hash-chained vote 
ledger with Merkle 
trees\n\n```\n┌─────────────────────────────────────────────────────────────────
────────────┐\n│                    IMMUTABLE VOTE LEDGER                       
│\n├────────────────────────────────────────────────────────────────────────────
─┤\n│                                                                           
   │\n│   Genesis    Vote 1      Vote 2      Vote 3      Vote N                 
│\n│   ┌─────┐   ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐                       
│\n│   │ 0x0 │◄──┤ h1  │◄───┤ h2  │◄───┤ h3  │◄───┤ hN  │  ← Hash Chain        
│\n│   └─────┘   └──┬──┘    └──┬──┘    └──┬──┘    └──┬──┘                       
│\n│                │          │          │          │                          
│\n│                ▼          ▼          ▼          ▼                          
│\n│              ┌─────────────────────────────────────┐                       
│\n│              │         Merkle Tree Root            │  ← Batch Proof        
│\n│              │            (every 1k votes)         │                       
│\n│              └─────────────────────────────────────┘                       
│\n│                              │                                             
│\n│                              ▼                                             
│\n│              ┌─────────────────────────────────────┐                       
│\n│              │      External Signature (opt)       │  ← Tamper Proof       
│\n│              └─────────────────────────────────────┘                       
│\n│                                                                            
│\n└────────────────────────────────────────────────────────────────────────────
─┘\n```\n\n**Key Features:**\n- Each vote includes `prev_hash` forming an 
immutable chain\n- Merkle roots every 1,000 votes for efficient verification\n- 
Exportable audit logs with integrity proofs\n- Tamper detection via hash 
verification\n\n**Schema Additions:**\n```sql\nCREATE TABLE vote_ledger (\n    
id INTEGER PRIMARY KEY AUTOINCREMENT,\n    fact_id INTEGER NOT NULL,\n    
agent_id TEXT NOT NULL,\n    vote INTEGER NOT NULL,\n    vote_weight REAL NOT 
NULL,\n    prev_hash TEXT NOT NULL,      -- Previous entry hash\n    hash TEXT 
NOT NULL,           -- SHA-256 of this entry\n    timestamp TEXT NOT NULL,\n    
signature TEXT                -- Optional Ed25519 signature\n);\n\nCREATE TABLE 
vote_merkle_roots (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    root_hash 
TEXT NOT NULL,\n    vote_start_id INTEGER NOT NULL,\n    vote_end_id INTEGER NOT
NULL,\n    vote_count INTEGER NOT NULL\n);\n```\n\n---\n\n### 2.2 Pillar 2: 
High-Availability Synchronization\n\n**Problem:** Single-node deployment with no
failover capability.\n\n**Solution:** Raft consensus + CRDT-based 
replication\n\n```\n┌───────────────────────────────────────────────────────────
──────────────────┐\n│                    HA CORTEX CLUSTER                     
│\n├────────────────────────────────────────────────────────────────────────────
─┤\n│                                                                           
   │\n│   ┌───────────────────────────────────────────────────────────────────┐ 
│\n│   │                    CONSENSUS LAYER (Raft)                          │   
│\n│   │                                                                    │   
│\n│   │    ┌─────────┐      ┌─────────┐      ┌─────────┐                  │    
│\n│   │    │ Node 1  │◄────►│ Node 2  │◄────►│ Node 3  │                  │    
│\n│   │    │ LEADER  │      │FOLLOWER │      │FOLLOWER │                  │    
│\n│   │    └────┬────┘      └────┬────┘      └────┬────┘                  │    
│\n│   │         │                │                │                        │   
│\n│   │         └────────────────┴────────────────┘                        │   
│\n│   │                      │                                             │   
│\n│   │                      ▼                                             │   
│\n│   │         ┌─────────────────────────┐                                │   
│\n│   │         │   Log Replication       │  ← Strong Consistency          │   
│\n│   │         │   (Majority Ack)        │                                │   
│\n│   │         └─────────────────────────┘                                │   
│\n│   └───────────────────────────────────────────────────────────────────┘    
│\n│                                    │                                       
│\n│                                    ▼                                       
│\n│   ┌───────────────────────────────────────────────────────────────────┐    
│\n│   │                    DATA LAYER (CRDT)                               │   
│\n│   │                                                                    │   
│\n│   │  Facts:     LWW (Last-Write-Wins) Register                        │    
│\n│   │  Votes:     OR-Set (Observed-Remove Set)                          │    
│\n│   │  Agents:    LWW Register with vector clock merge                  │    
│\n│   │                                                                    │   
│\n│   │  Sync: Anti-entropy gossip every 30s                              │    
│\n│   └───────────────────────────────────────────────────────────────────┘    
│\n│                                                                            
│\n└────────────────────────────────────────────────────────────────────────────
─┘\n```\n\n**Key Features:**\n- **Raft Consensus:** Leader election, log 
replication, automatic failover\n- **CRDT Data Types:** Conflict-free replicated
data types for automatic merge\n- **Vector Clocks:** Causality tracking for 
concurrent updates\n- **Merkle Trees:** Efficient diff for synchronization\n- 
**Anti-Entropy Gossip:** Epidemic broadcast for eventual 
consistency\n\n**Consistency Model:**\n| Operation | Consistency | Mechanism 
|\n|-----------|-------------|-----------|\n| Vote casting | Strong | Raft 
consensus (majority ack) |\n| Fact reads | Eventual | CRDT with anti-entropy 
|\n| Agent updates | Eventual | LWW with vector clocks |\n| Ledger queries | 
Strong | Routed to leader |\n\n---\n\n### 2.3 Pillar 3: Edge-Optimized MCP 
Server\n\n**Problem:** Current MCP server is single-threaded with no caching or 
resource limits.\n\n**Solution:** Async multi-transport server with multi-tier 
caching\n\n```\n┌───────────────────────────────────────────────────────────────
──────────────┐\n│                    EDGE-OPTIMIZED MCP SERVER                 
│\n├────────────────────────────────────────────────────────────────────────────
─┤\n│                                                                           
   │\n│  ┌─────────────────────────────────────────────────────────────────────┐
│\n│  │  Transport Layer: stdio | SSE | WebSocket | HTTP/2                  │   
│\n│  └────────────────────────────────┬────────────────────────────────────┘   
│\n│                                   │                                        
│\n│  ┌────────────────────────────────▼────────────────────────────────────┐   
│\n│  │  Optimization Layer                                                 │   
│\n│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐       │   
│\n│  │  │ Multi-Tier   │  │   Request    │  │   Circuit Breaker   │       │   
│\n│  │  │ Cache        │  │   Batching   │  │   (Fault Tolerance) │       │   
│\n│  │  │ ┌──────────┐ │  │              │  │                     │       │   
│\n│  │  │ │ L1: LRU  │ │  │ Flush: 10ms  │  │ Failure: 5          │       │   
│\n│  │  │ │ L2: Redis│ │  │ Max: 100 ops │  │ Timeout: 30s        │       │   
│\n│  │  │ └──────────┘ │  │              │  │ Cooldown: 5s        │       │   
│\n│  │  └──────────────┘  └──────────────┘  └─────────────────────┘       │   
│\n│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐       │   
│\n│  │  │ Connection   │  │   Resource   │  │     Metrics         │       │   
│\n│  │  │ Pool (5)     │  │    Limits    │  │   (Prometheus)      │       │   
│\n│  │  │              │  │              │  │                     │       │   
│\n│  │  │ WAL mode     │  │ Memory: 256MB│  │ Latency P99         │       │   
│\n│  │  │ Async I/O    │  │ CPU: 1 core  │  │ Cache hit rate      │       │   
│\n│  │  └──────────────┘  └──────────────┘  └─────────────────────┘       │   
│\n│  └────────────────────────────────────────────────────────────────────┘   
│\n│                                                                            
│\n└────────────────────────────────────────────────────────────────────────────
─┘\n```\n\n**Key Features:**\n- **Multi-Transport:** stdio (default), SSE, 
WebSocket, HTTP/2\n- **Multi-Tier Cache:** L1 in-memory LRU, L2 Redis 
(optional)\n- **Request Batching:** Automatic batching of writes (10ms flush, 
100 ops max)\n- **Circuit Breaker:** Fault tolerance with automatic recovery\n- 
**Resource Monitoring:** Memory/CPU limits with graceful degradation\n- 
**Connection Pooling:** Async SQLite connection pool (WAL mode)\n\n**Performance
Targets:**\n| Metric | Current | Target | Improvement 
|\n|--------|---------|--------|-------------|\n| Warm search | 50ms | 1ms | 
**50x** |\n| Batch store (100) | 2300ms | 450ms | **5x** |\n| Throughput | 100 
req/s | 1000 req/s | **10x** |\n| Memory usage | Unbounded | <256MB | 
**Bounded** |\n| P99 latency | Variable | <10ms | **Consistent** |\n\n---\n\n## 
3. Integration Architecture\n\n### 3.1 How the Three Pillars Work 
Together\n\n```\n┌──────────────────────────────────────────────────────────────
───────────────┐\n│                    WAVE 5 INTEGRATED ARCHITECTURE           
│\n├────────────────────────────────────────────────────────────────────────────
─┤\n│                                                                           
   │\n│  ┌─────────────────────────────────────────────────────────────────────┐
│\n│  │                         CLIENT LAYER                                 │  
│\n│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │   
│\n│  │  │  CLI Client  │  │  REST Client │  │    MCP Client (Edge)     │   │   
│\n│  │  └──────┬───────┘  └──────┬───────┘  └───────────┬──────────────┘   │   
│\n│  │         │                 │                      │                  │   
│\n│  └─────────┼─────────────────┼──────────────────────┼──────────────────┘   
│\n│            │                 │                      │                      
│\n│            ▼                 ▼                      ▼                      
│\n│  ┌─────────────────────────────────────────────────────────────────────┐   
│\n│  │                      CORTEX CLUSTER (3+ nodes)                       │  
│\n│  │                                                                      │  
│\n│  │  ┌───────────────────────────────────────────────────────────────┐  │   
│\n│  │  │              PILLAR 2: HA SYNCHRONIZATION                      │  │  
│\n│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐                       │  │   
│\n│  │  │  │ Node 1  │◄►│ Node 2  │◄►│ Node 3  │  ← Raft + CRDT        │  │   
│\n│  │  │  │ (Leader)│  │(Follower)│  │(Follower)│                      │  │   
│\n│  │  │  └────┬────┘  └────┬────┘  └────┬────┘                       │  │   
│\n│  │  │       └─────────────┴─────────────┘                            │  │  
│\n│  │  │                    │                                           │  │  
│\n│  │  └────────────────────┼───────────────────────────────────────────┘  │  
│\n│  │                       │                                              │  
│\n│  │  ┌────────────────────▼───────────────────────────────────────────┐  │  
│\n│  │  │              PILLAR 1: IMMUTABLE VOTE LEDGER                    │  │ 
│\n│  │  │                                                                 │  │ 
│\n│  │  │  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │  │  
│\n│  │  │  │ Vote Cast    │────►│ Hash Chain   │────►│ Merkle Root  │    │  │  
│\n│  │  │  │ (Event)      │     │ (SHA-256)    │     │ (Batch)      │    │  │  
│\n│  │  │  └──────────────┘     └──────────────┘     └──────────────┘    │  │  
│\n│  │  │                                                                 │  │ 
│\n│  │  │  Every vote is:                                                   │  
│   │\n│  │  │  1. Appended to hash-chained ledger                              
│  │   │\n│  │  │  2. Replicated via Raft (strong consistency)                  
│  │   │\n│  │  │  3. Periodically batched into Merkle tree                     
│  │   │\n│  │  │                                                               
│  │   │\n│  │  
└─────────────────────────────────────────────────────────────────┘  │   │\n│  │
│   │\n│  
└───────────────────────────────────────────────────────────────────────┘   │\n│
│\n│  ┌─────────────────────────────────────────────────────────────────────┐   
│\n│  │              PILLAR 3: EDGE MCP SERVER (Per-Node)                    │  
│\n│  │                                                                      │  
│\n│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐        │   
│\n│  │  │ Multi-Transport│  │ Multi-Tier   │  │   Resource          │        │ 
│\n│  │  │ (stdio/SSE/   │  │ Cache        │  │   Monitoring        │        │  
│\n│  │  │  WebSocket)   │  │ (L1/L2)      │  │   (256MB limit)     │        │  
│\n│  │  └──────────────┘  └──────────────┘  └─────────────────────┘        │   
│\n│  │                                                                      │  
│\n│  │  Each node runs edge-optimized MCP server for local queries          │  
│\n│  │                                                                      │  
│\n│  └─────────────────────────────────────────────────────────────────────┘   
│\n│                                                                            
│\n└────────────────────────────────────────────────────────────────────────────
─┘\n```\n\n### 3.2 Data Flow: Casting a Vote\n\n```\n1. Client sends vote 
request to MCP server\n        │\n        ▼\n2. Edge MCP server receives 
request\n   ├── Check circuit breaker\n   ├── Acquire connection from pool\n   
└── Forward to local engine\n        │\n        ▼\n3. Local engine processes 
vote\n   ├── Verify agent reputation\n   ├── Record vote in consensus_votes_v2\n
├── Append to vote_ledger (hash chain)\n   └── Recalculate consensus score\n    
│\n        ▼\n4. HA Sync replicates vote (if leader)\n   ├── Append to Raft 
log\n   ├── Replicate to followers\n   └── Wait for majority ack\n        │\n   
▼\n5. Followers apply vote\n   ├── Update local consensus_votes_v2\n   ├── 
Append to local vote_ledger\n   └── Update Merkle tree\n        │\n        ▼\n6.
Response returned to client\n   ├── Vote confirmed\n   ├── New consensus score\n
└── Ledger entry hash\n```\n\n---\n\n## 4. Deployment Topologies\n\n### 4.1 
Single-Node (Development)\n\n```\n┌─────────────────────────────────────────┐\n│
Development Workstation       │\n│                                         │\n│ 
┌─────────────────────────────────┐   │\n│  │  CORTEX Single Node             │ 
│\n│  │                                 │   │\n│  │  ┌──────────┐  ┌──────────┐ 
│   │\n│  │  │   API    │  │   MCP    │    │   │\n│  │  │  Server  │  │  Server 
│    │   │\n│  │  └────┬─────┘  └────┬─────┘    │   │\n│  │       
└─────────────┘          │   │\n│  │              │                  │   │\n│  │
┌──────▼──────┐           │   │\n│  │       │   SQLite    │           │   │\n│  
│       │  (Single)   │           │   │\n│  │       └─────────────┘           │ 
│\n│  │                                 │   │\n│  
└─────────────────────────────────┘   │\n│                                      
│\n└─────────────────────────────────────────┘\n```\n\n### 4.2 Three-Node HA 
Cluster 
(Production)\n\n```\n┌──────────────────────────────────────────────────────────
───────────────────┐\n│                         Production Cluster              
│\n├────────────────────────────────────────────────────────────────────────────
─┤\n│                                                                           
   │\n│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐       
│\n│  │     Node 1       │  │     Node 2       │  │     Node 3       │          
│\n│  │    (Leader)      │  │   (Follower)     │  │   (Follower)     │          
│\n│  │                  │  │                  │  │                  │          
│\n│  │  ┌────────────┐  │  │  ┌────────────┐  │  │  ┌────────────┐  │          
│\n│  │  │ API Server │  │  │  │ API Server │  │  │  │ API Server │  │          
│\n│  │  │  (Primary) │  │  │  │ (Replica)  │  │  │  │ (Replica)  │  │          
│\n│  │  └────────────┘  │  │  └────────────┘  │  │  └────────────┘  │          
│\n│  │  ┌────────────┐  │  │  ┌────────────┐  │  │  ┌────────────┐  │          
│\n│  │  │ Edge MCP   │  │  │  │ Edge MCP   │  │  │  │ Edge MCP   │  │          
│\n│  │  │  Server    │  │  │  │  Server    │  │  │  │  Server    │  │          
│\n│  │  └────────────┘  │  │  └────────────┘  │  │  └────────────┘  │          
│\n│  │  ┌────────────┐  │  │  ┌────────────┐  │  │  ┌────────────┐  │          
│\n│  │  │   SQLite   │  │  │  │   SQLite   │  │  │  │   SQLite   │  │          
│\n│  │  │  (Local)   │◄─┼──┼─►│  (Local)   │◄─┼──┼─►│  (Local)   │  │          
│\n│  │  └────────────┘  │  │  └────────────┘  │  │  └────────────┘  │          
│\n│  │                  │  │                  │  │                  │          
│\n│  │  ┌────────────┐  │  │  ┌────────────┐  │  │  ┌────────────┐  │          
│\n│  │  │   Raft     │◄─┼──┼─►│   Raft     │◄─┼──┼─►│   Raft     │  │          
│\n│  │  │  (Leader)  │  │  │  │(Follower)  │  │  │  │(Follower)  │  │          
│\n│  │  └────────────┘  │  │  └────────────┘  │  │  └────────────┘  │          
│\n│  │                  │  │                  │  │                  │          
│\n│  └──────────────────┘  └──────────────────┘  └──────────────────┘          
│\n│           ▲                    ▲                    ▲                      
│\n│           └────────────────────┴────────────────────┘                      
│\n│                         Load Balancer                                      
│\n│                              │                                             
│\n│                         ┌────┴────┐                                        
│\n│                         │ Clients │                                        
│\n│                         └─────────┘                                        
│\n│                                                                            
│\n└────────────────────────────────────────────────────────────────────────────
─┘\n```\n\n### 4.3 Edge Deployment 
(IoT/ARM)\n\n```\n┌─────────────────────────────────────────────────────────────
────────────────┐\n│                         Edge Deployment                    
│\n├────────────────────────────────────────────────────────────────────────────
─┤\n│                                                                           
   │\n│  ┌─────────────────────────────────────────────────────────────────────┐
│\n│  │                    Edge Device (Raspberry Pi / ARM)                  │  
│\n│  │                                                                      │  
│\n│  │  ┌───────────────────────────────────────────────────────────────┐  │   
│\n│  │  │              CORTEX Edge Node                                  │  │  
│\n│  │  │                                                                │  │  
│\n│  │  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐  │  │   
│\n│  │  │  │  Edge MCP    │  │  Local Cache │  │  SQLite (WAL mode)  │  │  │   
│\n│  │  │  │  Server      │  │  (LRU 500)   │  │  (128MB limit)      │  │  │   
│\n│  │  │  │              │  │              │  │                     │  │  │   
│\n│  │  │  │  - stdio     │  │  - Facts     │  │  - Local facts      │  │  │   
│\n│  │  │  │  - SSE       │  │  - Embeddings│  │  - Local votes      │  │  │   
│\n│  │  │  │  (no WS)     │  │              │  │  - Sync queue       │  │  │   
│\n│  │  │  └──────────────┘  └──────────────┘  └─────────────────────┘  │  │   
│\n│  │  │                                                                │  │  
│\n│  │  │  Resource Limits:                                               │  │ 
│\n│  │  │  - Memory: 128MB                                                │  │ 
│\n│  │  │  - CPU: 0.5 cores                                               │  │ 
│\n│  │  │  - Storage: 1GB                                                 │  │ 
│\n│  │  │                                                                │  │  
│\n│  │  └───────────────────────────────────────────────────────────────┘  │   
│\n│  │                                                                      │  
│\n│  │  Periodic Sync (when connected):                                    │   
│\n│  │  ┌──────────────┐         ┌──────────────┐                         │   
│\n│  │  │  Edge Node   │◄───────►│  Hub Node    │                         │   
│\n│  │  │  (Offline)   │  WiFi   │  (Online)    │                         │   
│\n│  │  └──────────────┘         └──────────────┘                         │   
│\n│  │                                                                      │  
│\n│  └─────────────────────────────────────────────────────────────────────┘   
│\n│                                                                            
│\n└────────────────────────────────────────────────────────────────────────────
─┘\n```\n\n---\n\n## 5. Security Analysis\n\n### 5.1 Threat Model & 
Mitigations\n\n| Threat | Severity | Mitigation 
|\n|--------|----------|------------|\n| **Vote Tampering** | Critical | 
Immutable ledger with Merkle trees; any modification breaks hash chain |\n| 
**Node Compromise** | High | Raft consensus requires majority; compromised node 
can't alter consensus |\n| **Network Partition** | Medium | CRDT merge 
strategies; automatic conflict resolution when partition heals |\n| **Replay 
Attacks** | Medium | Vector clocks + timestamps; duplicate votes detected and 
rejected |\n| **Sybil Attacks** | Medium | Reputation-weighted consensus (Wave 
4); new agents have low reputation |\n| **DoS** | Medium | Circuit breaker + 
rate limiting; graceful degradation under load |\n| **Eavesdropping** | Low | 
TLS for inter-node communication; encrypted replication |\n| **Data Loss** | Low
| Multi-node replication; automatic failover; regular backups |\n\n### 5.2 Audit
& Compliance\n\n**Immutable Vote Ledger provides:**\n- Complete audit trail of 
all consensus decisions\n- Cryptographic proof of vote ordering and timing\n- 
Exportable logs for external auditors\n- Tamper detection with automated 
alerts\n- Optional external anchoring (blockchain, timestamp 
services)\n\n---\n\n## 6. Performance Projections\n\n### 6.1 Vote 
Processing\n\n| Scenario | Latency | Throughput 
|\n|----------|---------|------------|\n| Single-node vote | 5ms | 200 votes/sec
|\n| HA cluster vote (leader) | 15ms | 500 votes/sec |\n| HA cluster vote 
(follower redirect) | 20ms | 400 votes/sec |\n| Batch vote (100 votes) | 100ms |
1000 votes/sec |\n\n### 6.2 Query Performance\n\n| Query Type | Cold | Warm 
(Cached) | Improvement |\n|------------|------|---------------|-------------|\n|
Semantic search | 50ms | 1ms | **50x** |\n| Fact recall | 10ms | 0.5ms | **20x**
|\n| Graph query | 30ms | 5ms | **6x** |\n| Ledger verification | 100ms (10k 
entries) | N/A | Baseline |\n\n### 6.3 Resource Usage\n\n| Deployment | Memory |
CPU | Storage |\n|------------|--------|-----|---------|\n| Single-node | 128MB 
| 0.5 cores | 1GB |\n| HA node | 256MB | 1 core | 5GB |\n| Edge device | 128MB |
0.5 cores | 1GB |\n\n---\n\n## 7. Migration Path\n\n### 7.1 From Wave 4 to Wave 
5\n\n```\nPhase 1: Immutable Vote Ledger (Week 1-2)\n├── Backup existing 
database\n├── Run migration 010 (vote_ledger schema)\n├── Deploy VoteLedger 
class\n├── Update vote() to append to ledger\n└── Verify: cortex vote-ledger 
verify\n\nPhase 2: HA Synchronization (Week 3-4)\n├── Deploy second node\n├── 
Run migration 011 (HA schema)\n├── Configure Raft cluster\n├── Test 
failover\n└── Verify: cortex cluster status\n\nPhase 3: Edge MCP (Week 5-6)\n├──
Deploy mcp_server_edge.py\n├── Configure caching\n├── Test performance 
benchmarks\n└── Verify: cortex benchmark --suite edge\n\nPhase 4: Production 
Cutover (Week 7-8)\n├── Deploy third node\n├── Update load balancer\n├── Monitor
metrics\n└── Document runbooks\n```\n\n### 7.2 Backward Compatibility\n\n- Wave 
5 is **backward compatible** with Wave 4 clients\n- Vote ledger is 
**append-only** — existing votes remain valid\n- HA cluster can operate with 
**mixed versions** during upgrade\n- Edge MCP server maintains **same protocol**
as standard MCP\n\n---\n\n## 8. Conclusion\n\nWave 5 transforms CORTEX from a 
development-ready system into a **production-grade sovereign memory 
infrastructure**:\n\n1. **Immutable Vote Logging** ensures cryptographic 
integrity of all consensus decisions\n2. **High-Availability Synchronization** 
provides automatic failover and geographic distribution\n3. **Edge-Optimized MCP
Server** enables deployment on resource-constrained devices\n\nTogether, these 
capabilities enable:\n- **Sovereign AI deployments** with tamper-evident 
consensus\n- **Enterprise-grade availability** with 99.9% uptime\n- **Edge 
computing scenarios** with sub-millisecond query latency\n\n**Next Steps:**\n1. 
Implement Migration 010 (Immutable Vote Ledger)\n2. Implement Migration 011 (HA 
Synchronization)\n3. Implement Edge MCP Server\n4. Load testing with 10k 
requests/sec\n5. Security audit and penetration testing\n6. Documentation and 
deployment guides\n\n---\n\n**End of Architecture Analysis**\n\n*Prepared for 
CORTEX V4.0 Wave 5 Implementation | 2026-02-16*"
            )
        ],
        extras=None
    )
)
StepBegin(n=8)
TextPart(
    type='text',
    text="I have completed a comprehensive analysis of the CORTEX V4.0 
architecture and created a detailed Wave 5 (Persistence & Deployment) proposal. 
Here's a summary of what was delivered:\n\n## Summary\n\n### Documents 
Created\n\n1. **`WAVE5_PROPOSAL_PERSISTENCE_DEPLOYMENT.md`** (82KB) — Complete 
technical specification including:\n   - Immutable Vote Logging with Merkle 
trees\n   - High-Availability Synchronization with Raft + CRDTs\n   - 
Edge-Optimized MCP Server with multi-tier caching\n\n2. 
**`WAVE5_ARCHITECTURE_ANALYSIS.md`** (44KB) — Executive summary and integration 
analysis\n\n### Key Wave 5 Components\n\n#### 1. Immutable Vote Logging\n- 
**Hash-chained vote ledger** — Each vote includes `prev_hash` forming an 
immutable chain\n- **Merkle tree batching** — Roots every 1,000 votes for 
efficient verification\n- **Tamper detection** — Automated integrity 
verification\n- **Exportable audit logs** — JSON/CSV with cryptographic 
proofs\n\n#### 2. High-Availability Synchronization\n- **Raft consensus** — 
Leader election, log replication, automatic failover\n- **CRDT data types** — 
Conflict-free replicated data types for automatic merge\n- **Vector clocks** — 
Causality tracking for concurrent updates\n- **Anti-entropy gossip** — Epidemic 
broadcast for eventual consistency\n\n#### 3. Edge-Optimized MCP Server\n- 
**Multi-transport** — stdio, SSE, WebSocket, HTTP/2\n- **Multi-tier caching** — 
L1 in-memory LRU, L2 Redis (optional)\n- **Request batching** — 10ms flush, 100 
ops max\n- **Circuit breaker** — Fault tolerance with automatic recovery\n- 
**Resource monitoring** — Memory/CPU limits (<256MB)\n\n### Performance 
Targets\n\n| Metric | Current | Target | Improvement 
|\n|--------|---------|--------|-------------|\n| Warm search | 50ms | 1ms | 
**50x** |\n| Batch store (100) | 2300ms | 450ms | **5x** |\n| Throughput | 100 
req/s | 1000 req/s | **10x** |\n| Memory usage | Unbounded | <256MB | 
**Bounded** |\n| HA Failover | N/A | <5s | **New** |\n\n### Migration Timeline 
(8 Weeks)\n- Weeks 1-2: Immutable Vote Ledger\n- Weeks 3-4: HA Synchronization  
\n- Weeks 5-6: Edge MCP Optimization\n- Weeks 7-8: Integration & Testing"
)
StatusUpdate(
    context_usage=0.3105125427246094,
    token_usage=TokenUsage(
        input_other=1783,
        output=544,
        input_cache_read=79616,
        input_cache_creation=0
    ),
    message_id='chatcmpl-Wdm7p38PgnLlHEAQbdvbyNpz'
)

# CORTEX V4.0 — Wave 5: Persistence & Deployment
## Production-Ready Consensus Infrastructure

**Date:** 2026-02-16  
**Version:** 5.0.0-proposal  
**Status:** Technical Design Document  
**Author:** CORTEX Architecture Team  

---

## Executive Summary

Wave 5 transforms CORTEX from a development-ready system into a **production-grade sovereign memory infrastructure**. Building upon the Reputation-Weighted Consensus (RWC) foundation from Wave 4, this wave delivers three critical capabilities:

1. **Immutable Vote Logging** — Cryptographically tamper-evident consensus audit trail
2. **High-Availability Ledger Synchronization** — Multi-node consensus with conflict-free replication
3. **Edge-Optimized MCP Server** — High-performance Model Context Protocol for distributed deployments

### Wave Completion Status

| Wave | Feature | Status |
|------|---------|--------|
| Wave 1 | Core Engine (Facts, Search, Embeddings) | ✅ Complete |
| Wave 2 | Temporal Facts & Transaction Ledger | ✅ Complete |
| Wave 3 | REST API, Auth, Dashboard | ✅ Complete |
| Wave 4 | Consensus Layer (RWC) | ✅ Complete |
| **Wave 5** | **Persistence & Deployment** | 🔄 **Proposed** |
| Wave 6 | Swarm Federation & Bridge Protocols | 📋 Planned |

---

## 1. Immutable Vote Logging

### 1.1 Problem Statement

The current consensus system has critical audit gaps:

```python
# Current Implementation (Wave 4)
# Votes are stored but NOT linked to the immutable ledger
conn.execute(
    "INSERT INTO consensus_votes_v2 (fact_id, agent_id, vote, vote_weight) ..."
)
# No cryptographic proof of vote existence
# No protection against "God Key" database admin attacks
# No external verifiability
```

**Vulnerabilities:**
- ❌ Votes can be modified by database administrators
- ❌ No cryptographic proof of vote ordering/timing
- ❌ No mechanism for external audit
- ❌ Vote history can be selectively deleted

### 1.2 Design Goals

| Goal | Priority | Description |
|------|----------|-------------|
| **Tamper-Proof** | P0 | Cryptographic guarantees against any modification |
| **Verifiable** | P0 | Third parties can verify integrity without trust |
| **Ordered** | P0 | Strict temporal ordering of all votes |
| **Efficient** | P1 | <5ms overhead per vote |
| **Exportable** | P1 | JSON/CSV export for external auditors |
| **Redundant** | P2 | Multiple storage backends (local + remote hash log) |

### 1.3 Architecture: Hierarchical Vote Ledger

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    IMMUTABLE VOTE LEDGER ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│   │  Vote Cast   │────▶│  Vote Entry  │────▶│  Hash Chain  │                │
│   │   (Event)    │     │  (SQLite)    │     │  (SHA-256)   │                │
│   └──────────────┘     └──────────────┘     └──────┬───────┘                │
│                                                     │                        │
│                              ┌──────────────────────┘                        │
│                              ▼                                               │
│   ┌────────────────────────────────────────────────────────────┐            │
│   │              MERKLE TREE LAYER (Batched)                    │            │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │            │
│   │  │  Batch 1    │  │  Batch 2    │  │  Batch N    │         │            │
│   │  │  Root: 0x.. │  │  Root: 0x.. │  │  Root: 0x.. │         │            │
│   │  │  1000 votes │  │  1000 votes │  │  1000 votes │         │            │
│   │  └─────────────┘  └─────────────┘  └─────────────┘         │            │
│   └────────────────────────────────────────────────────────────┘            │
│                              │                                               │
│                              ▼                                               │
│   ┌────────────────────────────────────────────────────────────┐            │
│   │              EXTERNAL SIGNATURE LAYER (Optional)            │            │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │            │
│   │  │  Signify    │  │  OpenPubKey │  │  Anchoring  │         │            │
│   │  │  (Sigstore) │  │  (SSH/PGP)  │  │  (Optional) │         │            │
│   │  └─────────────┘  └─────────────┘  └─────────────┘         │            │
│   └────────────────────────────────────────────────────────────┘            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.4 Database Schema Extensions

```sql
-- ============================================================
-- MIGRATION 010: Immutable Vote Ledger
-- ============================================================

-- Vote ledger: Append-only, hash-chained record of all votes
CREATE TABLE vote_ledger (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Vote reference
    fact_id         INTEGER NOT NULL REFERENCES facts(id),
    agent_id        TEXT NOT NULL REFERENCES agents(id),
    vote            INTEGER NOT NULL,  -- +1 (verify), -1 (dispute)
    vote_weight     REAL NOT NULL,
    
    -- Cryptographic chain
    prev_hash       TEXT NOT NULL,      -- Previous vote ledger entry hash
    hash            TEXT NOT NULL,      -- SHA-256 of this entry
    
    -- Temporal proof
    timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
    
    -- Optional: External verification
    signature       TEXT,               -- Ed25519 signature by agent
    
    -- Index for efficient verification
    UNIQUE(hash)
);

CREATE INDEX idx_vote_ledger_fact ON vote_ledger(fact_id);
CREATE INDEX idx_vote_ledger_agent ON vote_ledger(agent_id);
CREATE INDEX idx_vote_ledger_timestamp ON vote_ledger(timestamp);

-- Merkle tree roots for periodic integrity verification
CREATE TABLE vote_merkle_roots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    root_hash       TEXT NOT NULL,              -- SHA-256 of combined vote hashes
    vote_start_id   INTEGER NOT NULL,           -- First vote in this batch
    vote_end_id     INTEGER NOT NULL,           -- Last vote in this batch
    vote_count      INTEGER NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    
    -- Optional: External proof-of-existence
    external_proof  TEXT,                       -- URL or hash of external anchor
    
    -- Signature by "God Key" (if configured)
    signature       TEXT                        -- Ed25519 signature of root_hash
);

CREATE INDEX idx_vote_merkle_range ON vote_merkle_roots(vote_start_id, vote_end_id);

-- Audit log export tracking
CREATE TABLE vote_audit_exports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    export_type     TEXT NOT NULL,              -- 'json', 'csv', 'chain'
    filename        TEXT NOT NULL,
    file_hash       TEXT NOT NULL,              -- SHA-256 of exported file
    vote_start_id   INTEGER NOT NULL,
    vote_end_id     INTEGER NOT NULL,
    exported_at     TEXT NOT NULL DEFAULT (datetime('now')),
    exported_by     TEXT NOT NULL               -- API key or agent ID
);

-- Tamper detection log (append-only by design)
CREATE TABLE vote_integrity_checks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    check_type      TEXT NOT NULL,              -- 'merkle', 'chain', 'full'
    status          TEXT NOT NULL,              -- 'ok', 'violation', 'error'
    details         TEXT,                       -- JSON with findings
    started_at      TEXT NOT NULL,
    completed_at    TEXT NOT NULL
);
```

### 1.5 Implementation: Immutable Vote Ledger

```python
# cortex/vote_ledger.py
"""
Immutable Vote Ledger — Cryptographic integrity for CORTEX consensus votes.

Features:
- Hash-chained vote entries
- Periodic Merkle tree generation
- Tamper detection via hash verification
- Export with integrity proofs
"""

import hashlib
import json
import sqlite3
from typing import List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class VoteEntry:
    """A single entry in the vote ledger."""
    id: int
    fact_id: int
    agent_id: str
    vote: int
    vote_weight: float
    prev_hash: str
    hash: str
    timestamp: str
    signature: Optional[str] = None


class VoteLedger:
    """
    Manages the cryptographic integrity of CORTEX consensus votes.
    
    Features:
    - Append-only hash-chained vote storage
    - Periodic Merkle tree generation
    - Tamper detection via hash verification
    - Export with integrity proofs
    """
    
    MERKLE_BATCH_SIZE = 1000  # Create Merkle root every N votes
    
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
    
    def _compute_hash(
        self,
        prev_hash: str,
        fact_id: int,
        agent_id: str,
        vote: int,
        vote_weight: float,
        timestamp: str
    ) -> str:
        """Compute the hash for a vote entry."""
        hash_input = f"{prev_hash}:{fact_id}:{agent_id}:{vote}:{vote_weight}:{timestamp}"
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    def append_vote(
        self,
        fact_id: int,
        agent_id: str,
        vote: int,
        vote_weight: float,
        signature: Optional[str] = None
    ) -> VoteEntry:
        """
        Append a vote to the immutable ledger.
        
        Args:
            fact_id: The fact being voted on
            agent_id: The voting agent
            vote: +1 (verify) or -1 (dispute)
            vote_weight: The weight of the vote (reputation-based)
            signature: Optional cryptographic signature
            
        Returns:
            The created VoteEntry with computed hash
        """
        # Get previous hash
        prev = self.conn.execute(
            "SELECT hash FROM vote_ledger ORDER BY id DESC LIMIT 1"
        ).fetchone()
        prev_hash = prev[0] if prev else "GENESIS"
        
        # Compute timestamp
        timestamp = datetime.utcnow().isoformat()
        
        # Compute hash
        entry_hash = self._compute_hash(
            prev_hash, fact_id, agent_id, vote, vote_weight, timestamp
        )
        
        # Insert vote entry
        cursor = self.conn.execute(
            """
            INSERT INTO vote_ledger 
            (fact_id, agent_id, vote, vote_weight, prev_hash, hash, timestamp, signature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (fact_id, agent_id, vote, vote_weight, prev_hash, entry_hash, timestamp, signature)
        )
        
        # Check if we need to create a Merkle checkpoint
        self._maybe_create_checkpoint()
        
        return VoteEntry(
            id=cursor.lastrowid,
            fact_id=fact_id,
            agent_id=agent_id,
            vote=vote,
            vote_weight=vote_weight,
            prev_hash=prev_hash,
            hash=entry_hash,
            timestamp=timestamp,
            signature=signature
        )
    
    def _maybe_create_checkpoint(self) -> Optional[int]:
        """Create a Merkle checkpoint if batch size is reached."""
        # Count votes since last checkpoint
        last = self.conn.execute(
            "SELECT MAX(vote_end_id) FROM vote_merkle_roots"
        ).fetchone()[0] or 0
        
        count = self.conn.execute(
            "SELECT COUNT(*) FROM vote_ledger WHERE id > ?",
            (last,)
        ).fetchone()[0]
        
        if count < self.MERKLE_BATCH_SIZE:
            return None
        
        return self.create_merkle_checkpoint()
    
    def create_merkle_checkpoint(self) -> Optional[int]:
        """
        Create a Merkle tree checkpoint for recent votes.
        Returns the checkpoint ID or None if no new votes.
        """
        # Find last checkpoint
        last = self.conn.execute(
            "SELECT MAX(vote_end_id) FROM vote_merkle_roots"
        ).fetchone()[0] or 0
        
        # Get range of votes to include
        start = last + 1
        end_row = self.conn.execute(
            "SELECT id FROM vote_ledger WHERE id > ? ORDER BY id LIMIT 1 OFFSET ?",
            (last, self.MERKLE_BATCH_SIZE - 1)
        ).fetchone()
        end = end_row[0] if end_row else start
        
        # Compute Merkle root
        root = self._compute_merkle_root(start, end)
        if not root:
            return None
        
        # Store checkpoint
        cursor = self.conn.execute(
            """INSERT INTO vote_merkle_roots 
                (root_hash, vote_start_id, vote_end_id, vote_count) 
                VALUES (?, ?, ?, ?)""",
            (root, start, end, end - start + 1)
        )
        
        return cursor.lastrowid
    
    def _compute_merkle_root(self, start_id: int, end_id: int) -> Optional[str]:
        """Compute Merkle root for a range of votes."""
        cursor = self.conn.execute(
            "SELECT hash FROM vote_ledger WHERE id >= ? AND id <= ? ORDER BY id",
            (start_id, end_id)
        )
        hashes = [row[0] for row in cursor.fetchall()]
        
        if not hashes:
            return None
        
        # Build Merkle tree
        while len(hashes) > 1:
            next_level = []
            for i in range(0, len(hashes), 2):
                left = hashes[i]
                right = hashes[i + 1] if i + 1 < len(hashes) else hashes[i]
                combined = hashlib.sha256((left + right).encode()).hexdigest()
                next_level.append(combined)
            hashes = next_level
        
        return hashes[0]
    
    def verify_chain_integrity(self) -> dict:
        """
        Verify the integrity of the entire vote ledger.
        
        Returns:
            Dict with verification results
        """
        violations = []
        
        # 1. Verify hash chain continuity
        votes = self.conn.execute(
            "SELECT id, prev_hash, hash, fact_id, agent_id, vote, vote_weight, timestamp "
            "FROM vote_ledger ORDER BY id"
        ).fetchall()
        
        prev_hash = "GENESIS"
        for vote in votes:
            vote_id, tx_prev, tx_hash, fact_id, agent_id, vote_val, weight, ts = vote
            
            # Verify prev_hash matches
            if tx_prev != prev_hash:
                violations.append({
                    "vote_id": vote_id,
                    "type": "chain_break",
                    "expected_prev": prev_hash,
                    "actual_prev": tx_prev
                })
            
            # Verify current hash
            computed = self._compute_hash(
                tx_prev, fact_id, agent_id, vote_val, weight, ts
            )
            
            if computed != tx_hash:
                violations.append({
                    "vote_id": vote_id,
                    "type": "hash_mismatch",
                    "computed": computed,
                    "stored": tx_hash
                })
            
            prev_hash = tx_hash
        
        # 2. Verify Merkle roots
        merkles = self.conn.execute(
            "SELECT id, root_hash, vote_start_id, vote_end_id FROM vote_merkle_roots ORDER BY id"
        ).fetchall()
        
        for m in merkles:
            m_id, stored_root, start, end = m
            computed_root = self._compute_merkle_root(start, end)
            
            if computed_root != stored_root:
                violations.append({
                    "merkle_id": m_id,
                    "type": "merkle_mismatch",
                    "range": f"{start}-{end}",
                    "computed": computed_root,
                    "stored": stored_root
                })
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "votes_checked": len(votes),
            "merkle_roots_checked": len(merkles)
        }
    
    def get_vote_history(self, fact_id: int) -> List[VoteEntry]:
        """Get the complete vote history for a fact."""
        cursor = self.conn.execute(
            "SELECT id, fact_id, agent_id, vote, vote_weight, prev_hash, hash, timestamp, signature "
            "FROM vote_ledger WHERE fact_id = ? ORDER BY id",
            (fact_id,)
        )
        
        return [
            VoteEntry(
                id=row[0],
                fact_id=row[1],
                agent_id=row[2],
                vote=row[3],
                vote_weight=row[4],
                prev_hash=row[5],
                hash=row[6],
                timestamp=row[7],
                signature=row[8]
            )
            for row in cursor.fetchall()
        ]
    
    def export_verifiable_log(self, output_path: str, start_id: int = 1) -> dict:
        """
        Export votes with integrity proofs.
        
        Args:
            output_path: Where to write the export (JSON format)
            start_id: Starting vote ID
            
        Returns:
            Export metadata with root hash for verification
        """
        votes = self.conn.execute(
            "SELECT * FROM vote_ledger WHERE id >= ? ORDER BY id",
            (start_id,)
        ).fetchall()
        
        # Build Merkle tree
        hashes = [v[6] for v in votes]  # hash column
        
        # Compute root
        root = hashes[0] if hashes else None
        while len(hashes) > 1:
            next_level = []
            for i in range(0, len(hashes), 2):
                left = hashes[i]
                right = hashes[i + 1] if i + 1 < len(hashes) else hashes[i]
                combined = hashlib.sha256((left + right).encode()).hexdigest()
                next_level.append(combined)
            hashes = next_level
            root = hashes[0] if hashes else None
        
        export_data = {
            "export": {
                "version": "1.0",
                "exported_at": datetime.utcnow().isoformat(),
                "start_id": start_id,
                "end_id": votes[-1][0] if votes else start_id,
                "vote_count": len(votes),
                "merkle_root": root
            },
            "votes": [
                {
                    "id": v[0],
                    "fact_id": v[1],
                    "agent_id": v[2],
                    "vote": v[3],
                    "vote_weight": v[4],
                    "prev_hash": v[5],
                    "hash": v[6],
                    "timestamp": v[7],
                    "signature": v[8]
                }
                for v in votes
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        # Compute file hash
        with open(output_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Record export
        self.conn.execute(
            """INSERT INTO vote_audit_exports 
                (export_type, filename, file_hash, vote_start_id, vote_end_id, exported_by)
                VALUES (?, ?, ?, ?, ?, ?)""",
            ("json", output_path, file_hash, 
             export_data["export"]["start_id"],
             export_data["export"]["end_id"],
             "system")
        )
        self.conn.commit()
        
        return {
            "output_path": output_path,
            "file_hash": file_hash,
            "merkle_root": root,
            "votes": len(votes)
        }
```

### 1.6 CLI Commands

```bash
# Create a Merkle checkpoint for votes
cortex vote-ledger checkpoint

# Verify vote ledger integrity
cortex vote-ledger verify
# Output: ✓ Chain valid (10,234 votes, 10 Merkle roots)
#         ✓ All Merkle roots verified
#         ✓ No tampering detected

# Export verifiable vote log
cortex vote-ledger export --format json --output votes_2024.json

# Get vote history for a fact
cortex vote-ledger history <fact_id>

# Import and verify external vote log
cortex vote-ledger verify-external votes_2024.json
```

---

## 2. High-Availability Ledger Synchronization

### 2.1 Problem Statement

Current CORTEX operates as a single-node system with no replication:

```
Current State:
┌─────────────┐
│  CORTEX     │
│  (Single)   │
│  SQLite     │
└─────────────┘
     │
     ▼
  [SPOF]  ← Single Point of Failure
```

**Limitations:**
- ❌ No failover capability
- ❌ No geographic distribution
- ❌ Consensus votes lost if node fails
- ❌ No read replicas for query scaling

### 2.2 Design Goals

| Goal | Priority | Description |
|------|----------|-------------|
| **Availability** | P0 | 99.9% uptime with automatic failover |
| **Consistency** | P0 | Strong consistency for votes, eventual for reads |
| **Partition Tolerance** | P0 | Continue operating during network splits |
| **Conflict Resolution** | P1 | Automatic merge for concurrent writes |
| **Scalability** | P2 | Horizontal scaling for read-heavy workloads |

### 2.3 Architecture: CRDT-Based Replication

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HIGH-AVAILABILITY CORTEX CLUSTER                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                    CONSENSUS LAYER (Raft)                          │    │
│   │  ┌─────────┐  ┌─────────┐  ┌─────────┐                           │    │
│   │  │  Node 1 │  │  Node 2 │  │  Node 3 │  ← Leader Election         │    │
│   │  │  Leader │◄─┤ Follower│◄─┤ Follower│                           │    │
│   │  └────┬────┘  └────┬────┘  └────┬────┘                           │    │
│   │       └─────────────┴─────────────┘                              │    │
│   │                     │                                            │    │
│   │                     ▼                                            │    │
│   │         ┌─────────────────────┐                                  │    │
│   │         │   Log Replication   │                                  │    │
│   │         │   (Strong Consistency)│                                │    │
│   │         └─────────────────────┘                                  │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                    DATA LAYER (CRDT)                               │    │
│   │                                                                    │    │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │    │
│   │  │   Node 1     │  │   Node 2     │  │   Node 3     │             │    │
│   │  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │             │    │
│   │  │ │  Facts   │ │  │ │  Facts   │ │  │ │  Facts   │ │             │    │
│   │  │ │ (CRDT)   │◄┼──┼►│ (CRDT)   │◄┼──┼►│ (CRDT)   │ │             │    │
│   │  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │             │    │
│   │  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │             │    │
│   │  │ │  Votes   │ │  │ │  Votes   │ │  │ │  Votes   │ │             │    │
│   │  │ │ (CRDT)   │◄┼──┼►│ (CRDT)   │◄┼──┼►│ (CRDT)   │ │             │    │
│   │  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │             │    │
│   │  └──────────────┘  └──────────────┘  └──────────────┘             │    │
│   │                                                                    │    │
│   │  Replication: Anti-entropy gossip (every 30s)                     │    │
│   │  Conflict Resolution: LWW for facts, OR-Set for votes             │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                    SYNC PROTOCOL                                   │    │
│   │                                                                    │    │
│   │  1. Vector Clocks: Track causality across nodes                   │    │
│   │  2. Merkle Trees: Efficient diff for synchronization              │    │
│   │  3. Bloom Filters: Quick "has this changed?" checks               │    │
│   │  4. Gossip Protocol: Epidemic broadcast for updates               │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.4 Database Schema Extensions

```sql
-- ============================================================
-- MIGRATION 011: High-Availability Synchronization
-- ============================================================

-- Node identity and cluster membership
CREATE TABLE cluster_nodes (
    node_id         TEXT PRIMARY KEY,
    node_name       TEXT NOT NULL,
    node_address    TEXT NOT NULL,          -- Host:port for communication
    node_region     TEXT,                   -- Geographic region
    is_active       BOOLEAN DEFAULT TRUE,
    is_voter        BOOLEAN DEFAULT TRUE,   -- Participates in Raft consensus
    joined_at       TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at    TEXT NOT NULL DEFAULT (datetime('now')),
    raft_role       TEXT,                   -- 'leader', 'follower', 'candidate'
    meta            TEXT DEFAULT '{}'
);

-- Vector clocks for causality tracking
CREATE TABLE vector_clocks (
    node_id         TEXT NOT NULL REFERENCES cluster_nodes(node_id),
    entity_type     TEXT NOT NULL,          -- 'fact', 'vote', 'agent'
    entity_id       TEXT NOT NULL,          -- ID of the entity
    version         INTEGER NOT NULL DEFAULT 0,
    timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (node_id, entity_type, entity_id)
);

-- Sync log for anti-entropy
CREATE TABLE sync_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id         TEXT NOT NULL REFERENCES cluster_nodes(node_id),
    sync_type       TEXT NOT NULL,          -- 'push', 'pull', 'full'
    entity_type     TEXT NOT NULL,
    entity_count    INTEGER NOT NULL,
    started_at      TEXT NOT NULL,
    completed_at    TEXT,
    status          TEXT,                   -- 'success', 'failed', 'partial'
    details         TEXT                    -- JSON with sync details
);

CREATE INDEX idx_sync_log_node ON sync_log(node_id, completed_at);

-- Conflict resolution log
CREATE TABLE conflict_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type     TEXT NOT NULL,
    entity_id       TEXT NOT NULL,
    conflict_type   TEXT NOT NULL,          -- 'concurrent_update', 'delete_update'
    node_a          TEXT NOT NULL,
    node_b          TEXT NOT NULL,
    resolution      TEXT NOT NULL,          -- 'lww', 'merge', 'manual'
    resolved_at     TEXT NOT NULL DEFAULT (datetime('now')),
    details         TEXT
);

-- Merkle tree for efficient diff
CREATE TABLE sync_merkle (
    node_id         TEXT NOT NULL,
    entity_type     TEXT NOT NULL,
    bucket          INTEGER NOT NULL,       -- Hash bucket
    merkle_root     TEXT NOT NULL,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (node_id, entity_type, bucket)
);
```

### 2.5 Implementation: HA Synchronization

```python
# cortex/ha_sync.py
"""
High-Availability Synchronization for CORTEX.

Features:
- Raft consensus for leader election
- CRDT-based data replication
- Anti-entropy gossip protocol
- Automatic conflict resolution
"""

import hashlib
import json
import sqlite3
import asyncio
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import random


class NodeRole(Enum):
    LEADER = "leader"
    FOLLOWER = "follower"
    CANDIDATE = "candidate"


@dataclass
class VectorClock:
    """Vector clock for causality tracking."""
    node_id: str
    counters: Dict[str, int]
    
    def increment(self) -> "VectorClock":
        """Increment this node's counter."""
        new_counters = self.counters.copy()
        new_counters[self.node_id] = new_counters.get(self.node_id, 0) + 1
        return VectorClock(self.node_id, new_counters)
    
    def compare(self, other: "VectorClock") -> Optional[str]:
        """
        Compare two vector clocks.
        Returns: 'before', 'after', 'concurrent', or 'equal'
        """
        all_nodes = set(self.counters.keys()) | set(other.counters.keys())
        
        dominates = False
        dominated = False
        
        for node in all_nodes:
            a = self.counters.get(node, 0)
            b = other.counters.get(node, 0)
            
            if a > b:
                dominates = True
            elif b > a:
                dominated = True
        
        if dominates and not dominated:
            return "after"
        elif dominated and not dominates:
            return "before"
        elif not dominates and not dominated:
            return "equal"
        else:
            return "concurrent"


@dataclass
class SyncState:
    """Current synchronization state."""
    node_id: str
    role: NodeRole
    leader_id: Optional[str]
    term: int
    last_heartbeat: datetime
    known_nodes: List[str]


class HASyncManager:
    """
    Manages high-availability synchronization for CORTEX.
    
    Features:
    - Raft consensus for leader election
    - CRDT-based conflict-free replication
    - Anti-entropy gossip protocol
    """
    
    def __init__(
        self,
        conn: sqlite3.Connection,
        node_id: str,
        node_address: str,
        peers: List[str],
        gossip_interval: float = 30.0
    ):
        self.conn = conn
        self.node_id = node_id
        self.node_address = node_address
        self.peers = peers
        self.gossip_interval = gossip_interval
        
        self.role = NodeRole.FOLLOWER
        self.leader_id: Optional[str] = None
        self.term = 0
        self.voted_for: Optional[str] = None
        
        self._running = False
        self._gossip_task: Optional[asyncio.Task] = None
    
    def initialize_node(self) -> None:
        """Register this node in the cluster."""
        self.conn.execute(
            """
            INSERT OR REPLACE INTO cluster_nodes 
            (node_id, node_name, node_address, is_active, raft_role)
            VALUES (?, ?, ?, TRUE, ?)
            """,
            (self.node_id, self.node_id, self.node_address, self.role.value)
        )
        self.conn.commit()
    
    async def start(self) -> None:
        """Start the HA sync manager."""
        self._running = True
        self.initialize_node()
        
        # Start gossip protocol
        self._gossip_task = asyncio.create_task(self._gossip_loop())
        
        # Start Raft election timeout
        asyncio.create_task(self._raft_loop())
    
    async def stop(self) -> None:
        """Stop the HA sync manager."""
        self._running = False
        if self._gossip_task:
            self._gossip_task.cancel()
    
    async def _gossip_loop(self) -> None:
        """Background task for anti-entropy gossip."""
        while self._running:
            try:
                await self._perform_gossip()
            except Exception as e:
                print(f"Gossip error: {e}")
            
            await asyncio.sleep(self.gossip_interval)
    
    async def _perform_gossip(self) -> None:
        """Perform anti-entropy with a random peer."""
        if not self.peers:
            return
        
        # Select random peer
        peer = random.choice(self.peers)
        
        # Get our Merkle roots
        our_roots = self._get_merkle_roots()
        
        # In real implementation, this would be an RPC call
        # For now, we simulate the sync process
        peer_roots = await self._fetch_peer_roots(peer)
        
        # Find differences
        diffs = self._find_merkle_diffs(our_roots, peer_roots)
        
        if diffs:
            # Sync missing data
            await self._sync_differences(peer, diffs)
    
    def _get_merkle_roots(self) -> Dict[str, Dict[int, str]]:
        """Get Merkle roots for all entity types."""
        cursor = self.conn.execute(
            "SELECT entity_type, bucket, merkle_root FROM sync_merkle WHERE node_id = ?",
            (self.node_id,)
        )
        
        roots: Dict[str, Dict[int, str]] = {}
        for row in cursor.fetchall():
            entity_type, bucket, root = row
            if entity_type not in roots:
                roots[entity_type] = {}
            roots[entity_type][bucket] = root
        
        return roots
    
    async def _fetch_peer_roots(self, peer: str) -> Dict[str, Dict[int, str]]:
        """Fetch Merkle roots from a peer."""
        # In real implementation: RPC call to peer
        # Placeholder for demonstration
        return {}
    
    def _find_merkle_diffs(
        self,
        our_roots: Dict[str, Dict[int, str]],
        peer_roots: Dict[str, Dict[int, str]]
    ) -> List[Tuple[str, int]]:
        """Find buckets that differ between nodes."""
        diffs = []
        
        all_types = set(our_roots.keys()) | set(peer_roots.keys())
        
        for entity_type in all_types:
            our_buckets = our_roots.get(entity_type, {})
            peer_buckets = peer_roots.get(entity_type, {})
            
            all_buckets = set(our_buckets.keys()) | set(peer_buckets.keys())
            
            for bucket in all_buckets:
                our_root = our_buckets.get(bucket)
                peer_root = peer_buckets.get(bucket)
                
                if our_root != peer_root:
                    diffs.append((entity_type, bucket))
        
        return diffs
    
    async def _sync_differences(
        self,
        peer: str,
        diffs: List[Tuple[str, int]]
    ) -> None:
        """Synchronize differences with a peer."""
        for entity_type, bucket in diffs:
            # In real implementation: fetch and merge entities
            pass
    
    async def _raft_loop(self) -> None:
        """Raft consensus loop for leader election."""
        while self._running:
            timeout = random.uniform(0.15, 0.3)  # 150-300ms election timeout
            
            await asyncio.sleep(timeout)
            
            if self.role == NodeRole.FOLLOWER:
                # Check if we haven't heard from leader
                # Transition to candidate
                await self._start_election()
    
    async def _start_election(self) -> None:
        """Start a Raft election."""
        self.term += 1
        self.role = NodeRole.CANDIDATE
        self.voted_for = self.node_id
        
        # Request votes from peers
        votes = 1  # Vote for self
        
        for peer in self.peers:
            # In real implementation: RPC call
            # Placeholder
            pass
        
        # Check if we won
        if votes > (len(self.peers) + 1) / 2:
            await self._become_leader()
    
    async def _become_leader(self) -> None:
        """Transition to leader role."""
        self.role = NodeRole.LEADER
        self.leader_id = self.node_id
        
        self.conn.execute(
            "UPDATE cluster_nodes SET raft_role = ? WHERE node_id = ?",
            (NodeRole.LEADER.value, self.node_id)
        )
        self.conn.commit()
        
        # Start sending heartbeats
        asyncio.create_task(self._send_heartbeats())
    
    async def _send_heartbeats(self) -> None:
        """Send heartbeat messages to followers."""
        while self._running and self.role == NodeRole.LEADER:
            for peer in self.peers:
                # In real implementation: RPC call
                pass
            
            await asyncio.sleep(0.05)  # 50ms heartbeat interval
    
    def replicate_vote(
        self,
        fact_id: int,
        agent_id: str,
        vote: int,
        vote_weight: float
    ) -> bool:
        """
        Replicate a vote to the cluster.
        Only the leader can accept writes.
        """
        if self.role != NodeRole.LEADER:
            # Forward to leader
            return False
        
        # Append to local log
        # Replicate to followers
        # Wait for majority acknowledgment
        
        return True
    
    def update_merkle_tree(self, entity_type: str, entity_id: str) -> None:
        """Update Merkle tree after entity change."""
        # Compute bucket from entity_id hash
        bucket = int(hashlib.md5(entity_id.encode()).hexdigest(), 16) % 256
        
        # Recompute Merkle root for this bucket
        # This is simplified - real implementation would recompute from entities
        new_root = hashlib.sha256(
            f"{entity_type}:{entity_id}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()
        
        self.conn.execute(
            """
            INSERT OR REPLACE INTO sync_merkle 
            (node_id, entity_type, bucket, merkle_root, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (self.node_id, entity_type, bucket, new_root)
        )
        self.conn.commit()
```

---

## 3. Edge Deployment via MCP Server Optimization

### 3.1 Problem Statement

Current MCP server has limitations for edge deployment:

| Aspect | Current | Edge Requirement |
|--------|---------|------------------|
| Transport | stdio only | Multiple transports (SSE, WebSocket, HTTP/2) |
| Concurrency | Blocking | Async with connection pooling |
| Caching | None | Multi-tier caching (LRU, distributed) |
| Batching | None | Multi-fact operations |
| Observability | Basic logging | Metrics, traces, structured logs |
| Resource Usage | Unbounded | Memory/CPU limits for edge devices |

### 3.2 Design Goals

| Goal | Priority | Description |
|------|----------|-------------|
| **Low Latency** | P0 | <10ms p99 for cached queries |
| **High Throughput** | P0 | >1000 req/s per node |
| **Resource Efficiency** | P0 | <256MB RAM, <1 CPU core |
| **Transport Flexibility** | P1 | stdio, SSE, WebSocket, HTTP/2 |
| **Edge Caching** | P1 | LRU + distributed cache support |
| **Observability** | P2 | Prometheus metrics, OpenTelemetry traces |

### 3.3 Architecture: Optimized MCP Server

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EDGE-OPTIMIZED MCP SERVER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                      Transport Layer                               │    │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐       │    │
│   │  │  stdio   │  │   SSE    │  │  HTTP/2  │  │  WebSocket   │       │    │
│   │  │(default) │  │ (server) │  │(streaming│  │ (real-time)  │       │    │
│   │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘       │    │
│   │       └─────────────┴─────────────┴───────────────┘               │    │
│   │                         │                                         │    │
│   │                         ▼                                         │    │
│   │              ┌─────────────────────┐                              │    │
│   │              │   Protocol Handler  │                              │    │
│   │              │   (MCP 2024-11-05)  │                              │    │
│   │              └──────────┬──────────┘                              │    │
│   └─────────────────────────┼─────────────────────────────────────────┘    │
│                             │                                               │
│   ┌─────────────────────────┼─────────────────────────────────────────┐    │
│   │              ┌──────────▼──────────┐                               │    │
│   │              │    Request Router   │                               │    │
│   │              └──────────┬──────────┘                               │    │
│   │                         │                                          │    │
│   │   ┌─────────────────────┼─────────────────────┐                   │    │
│   │   │                     │                     │                   │    │
│   │   ▼                     ▼                     ▼                   │    │
│   │ ┌──────────┐      ┌──────────┐      ┌──────────────────┐         │    │
│   │ │  Tools   │      │Resources │      │  Prompt Templates │         │    │
│   │ │ Registry │      │ Registry │      │    Registry      │         │    │
│   │ └────┬─────┘      └────┬─────┘      └────────┬─────────┘         │    │
│   │      │                 │                     │                   │    │
│   └──────┼─────────────────┼─────────────────────┼───────────────────┘    │
│          │                 │                     │                         │
│   ┌──────▼─────────────────▼─────────────────────▼────────────────────┐   │
│   │                     Optimization Layer                             │   │
│   │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐     │   │
│   │  │  Multi-Tier  │  │   Request    │  │   Connection Pool   │     │   │
│   │  │    Cache     │  │   Batching   │  │    (SQLite WAL)     │     │   │
│   │  │ ┌──────────┐ │  │              │  │                     │     │   │
│   │  │ │  L1:     │ │  │ ┌──────────┐ │  │ ┌─────────────────┐ │     │   │
│   │  │ │ In-Memory│ │  │ │  Batch   │ │  │ │  Async Pool     │ │     │   │
│   │  │ └──────────┘ │  │ │  Queue   │ │  │ │  (5 conns)      │ │     │   │
│   │  │ ┌──────────┐ │  │ └──────────┘ │  │ └─────────────────┘ │     │   │
│   │  │ │  L2:     │ │  │              │  │                     │     │   │
│   │  │ │  Redis   │ │  │ Flush: 10ms  │  │                     │     │   │
│   │  │ │(optional)│ │  │ Max: 100 ops │  │                     │     │   │
│   │  │ └──────────┘ │  │              │  │                     │     │   │
│   │  └──────────────┘  └──────────────┘  └─────────────────────┘     │   │
│   │                                                                    │   │
│   │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐     │   │
│   │  │   Circuit    │  │   Resource   │  │     Metrics         │     │   │
│   │  │   Breaker    │  │    Limits    │  │   (Prometheus)      │     │   │
│   │  │              │  │              │  │                     │     │   │
│   │  │ Failure: 5   │  │ Memory: 256MB│  │ - Request latency   │     │   │
│   │  │ Timeout: 30s │  │ CPU: 1 core  │  │ - Cache hit rate    │     │   │
│   │  │ Cooldown: 5s │  │ Conns: 100   │  │ - Error rate        │     │   │
│   │  └──────────────┘  └──────────────┘  └─────────────────────┘     │   │
│   └────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                      Engine Layer                                  │    │
│   │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐     │    │
│   │  │Query Cache   │  │ Write-Ahead  │  │   Embedding Cache   │     │    │
│   │  │   (LRU)      │  │   Buffer     │  │    (LRU 100)        │     │    │
│   │  └──────────────┘  └──────────────┘  └─────────────────────┘     │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 Implementation: Edge-Optimized MCP Server

```python
# cortex/mcp_server_edge.py
"""
CORTEX MCP Server Edge — High-Performance Multi-Transport Implementation.

Features:
- Async I/O with connection pooling
- Multiple transports (stdio, SSE, WebSocket, HTTP/2)
- Multi-tier caching (L1 in-memory, L2 Redis)
- Request batching
- Circuit breaker pattern
- Resource limits
- Comprehensive metrics
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import resource
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union
from enum import Enum

import sqlite3
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("cortex.mcp.edge")


# ─────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class EdgeMCPConfig:
    """Configuration for edge-optimized MCP server."""
    db_path: str = "~/.cortex/cortex.db"
    max_workers: int = 4
    
    # Caching
    query_cache_size: int = 1000
    embedding_cache_size: int = 100
    cache_ttl_seconds: float = 300.0  # 5 minutes
    
    # Batching
    batch_size: int = 100
    batch_flush_ms: float = 10.0
    
    # Resource limits
    max_memory_mb: int = 256
    max_connections: int = 100
    
    # Circuit breaker
    circuit_failure_threshold: int = 5
    circuit_timeout_seconds: float = 30.0
    circuit_cooldown_seconds: float = 5.0
    
    # Metrics
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    # Transport
    transport: str = "stdio"  # "stdio", "sse", "websocket", "http2"
    host: str = "127.0.0.1"
    port: int = 9999
    keepalive_interval: float = 30.0


# ─────────────────────────────────────────────────────────────────────────
# Circuit Breaker
# ─────────────────────────────────────────────────────────────────────────

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: float = 30.0,
        cooldown_seconds: float = 5.0
    ):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.cooldown_seconds = cooldown_seconds
        
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - (self.last_failure_time or 0) > self.cooldown_seconds:
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.timeout_seconds
            )
            
            async with self._lock:
                if self.state == CircuitState.HALF_OPEN:
                    self.state = CircuitState.CLOSED
                self.failures = 0
            
            return result
            
        except Exception as e:
            async with self._lock:
                self.failures += 1
                self.last_failure_time = time.time()
                
                if self.failures >= self.failure_threshold:
                    self.state = CircuitState.OPEN
            
            raise


# ─────────────────────────────────────────────────────────────────────────
# Multi-Tier Cache
# ─────────────────────────────────────────────────────────────────────────

class MultiTierCache:
    """
    Multi-tier cache with L1 (in-memory) and L2 (Redis) layers.
    For edge deployment, L2 is optional.
    """
    
    def __init__(
        self,
        l1_size: int = 1000,
        ttl_seconds: float = 300.0,
        redis_url: Optional[str] = None
    ):
        self.l1_size = l1_size
        self.ttl_seconds = ttl_seconds
        self._l1: Dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
        
        # L2 cache (Redis) - optional for edge
        self._l2 = None
        if redis_url:
            try:
                import redis.asyncio as redis
                self._l2 = redis.from_url(redis_url)
            except ImportError:
                logger.warning("Redis not available, using L1 cache only")
    
    def _key(self, prefix: str, **params) -> str:
        """Generate cache key from parameters."""
        sorted_params = sorted(params.items())
        param_str = json.dumps(sorted_params, sort_keys=True)
        return f"{prefix}:{hashlib.md5(param_str.encode()).hexdigest()}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        now = time.time()
        
        # Check L1
        async with self._lock:
            if key in self._l1:
                value, expiry = self._l1[key]
                if expiry > now:
                    return value
                else:
                    del self._l1[key]
        
        # Check L2 (if available)
        if self._l2:
            try:
                value = await self._l2.get(key)
                if value:
                    data = json.loads(value)
                    # Promote to L1
                    async with self._lock:
                        self._l1[key] = (data, now + self.ttl_seconds)
                    return data
            except Exception as e:
                logger.warning("L2 cache error: %s", e)
        
        return None
    
    async def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        now = time.time()
        expiry = now + self.ttl_seconds
        
        # Set L1
        async with self._lock:
            # Evict oldest if at capacity
            while len(self._l1) >= self.l1_size:
                oldest_key = min(self._l1.keys(), key=lambda k: self._l1[k][1])
                del self._l1[oldest_key]
            
            self._l1[key] = (value, expiry)
        
        # Set L2 (if available)
        if self._l2:
            try:
                await self._l2.setex(
                    key,
                    int(self.ttl_seconds),
                    json.dumps(value)
                )
            except Exception as e:
                logger.warning("L2 cache error: %s", e)
    
    async def invalidate(self, pattern: str) -> None:
        """Invalidate cache entries matching pattern."""
        async with self._lock:
            keys_to_remove = [k for k in self._l1.keys() if pattern in k]
            for k in keys_to_remove:
                del self._l1[k]
        
        if self._l2:
            try:
                # Note: This is inefficient, production would use Redis SCAN
                pass
            except Exception as e:
                logger.warning("L2 cache error: %s", e)


# ─────────────────────────────────────────────────────────────────────────
# Request Batcher
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class BatchItem:
    """Single item in a batch."""
    request: dict
    future: asyncio.Future


class RequestBatcher:
    """Batches multiple requests for efficient processing."""
    
    def __init__(self, max_size: int = 100, flush_ms: float = 10.0):
        self.max_size = max_size
        self.flush_ms = flush_ms
        self._batch: List[BatchItem] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
    
    async def add(self, request: dict) -> asyncio.Future:
        """Add a request to the batch."""
        future = asyncio.get_event_loop().create_future()
        item = BatchItem(request, future)
        
        async with self._lock:
            self._batch.append(item)
            
            if len(self._batch) >= self.max_size:
                await self._flush()
            elif self._flush_task is None:
                self._flush_task = asyncio.create_task(self._delayed_flush())
        
        return future
    
    async def _delayed_flush(self) -> None:
        """Flush batch after delay."""
        await asyncio.sleep(self.flush_ms / 1000)
        async with self._lock:
            await self._flush()
            self._flush_task = None
    
    async def _flush(self) -> None:
        """Process all batched requests."""
        if not self._batch:
            return
        
        batch = self._batch[:]
        self._batch = []
        
        # Process batch
        # In real implementation, this would execute batch query
        for item in batch:
            try:
                result = await self._process_single(item.request)
                item.future.set_result(result)
            except Exception as e:
                item.future.set_exception(e)
    
    async def _process_single(self, request: dict) -> dict:
        """Process a single request."""
        # Placeholder - real implementation would batch SQL operations
        return {"status": "ok"}


# ─────────────────────────────────────────────────────────────────────────
# Resource Monitor
# ─────────────────────────────────────────────────────────────────────────

class ResourceMonitor:
    """Monitor and enforce resource limits."""
    
    def __init__(self, max_memory_mb: int = 256, max_connections: int = 100):
        self.max_memory_mb = max_memory_mb
        self.max_connections = max_connections
        self.active_connections = 0
        self._lock = asyncio.Lock()
    
    def check_memory(self) -> bool:
        """Check if memory usage is within limits."""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            return memory_mb < self.max_memory_mb
        except ImportError:
            # Fallback: use resource module
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            memory_mb = usage.ru_maxrss / 1024  # KB to MB
            return memory_mb < self.max_memory_mb
    
    @asynccontextmanager
    async def acquire_connection(self):
        """Acquire a connection slot."""
        async with self._lock:
            if self.active_connections >= self.max_connections:
                raise Exception("Max connections exceeded")
            self.active_connections += 1
        
        try:
            yield
        finally:
            async with self._lock:
                self.active_connections -= 1
    
    def get_stats(self) -> dict:
        """Get resource statistics."""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()
        except ImportError:
            memory_mb = 0
            cpu_percent = 0
        
        return {
            "memory_mb": memory_mb,
            "memory_limit_mb": self.max_memory_mb,
            "active_connections": self.active_connections,
            "max_connections": self.max_connections,
            "cpu_percent": cpu_percent
        }


# ─────────────────────────────────────────────────────────────────────────
# Edge-Optimized MCP Server
# ─────────────────────────────────────────────────────────────────────────

class EdgeMCPServer:
    """
    Edge-optimized MCP server for CORTEX.
    
    Features:
    - Multi-tier caching
    - Request batching
    - Circuit breaker
    - Resource monitoring
    - Multiple transports
    """
    
    def __init__(self, config: Optional[EdgeMCPConfig] = None):
        self.config = config or EdgeMCPConfig()
        self.metrics = MCPMetrics()
        self.pool: Optional[AsyncConnectionPool] = None
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        
        # Components
        self.cache = MultiTierCache(
            l1_size=self.config.query_cache_size,
            ttl_seconds=self.config.cache_ttl_seconds
        )
        self.batcher = RequestBatcher(
            max_size=self.config.batch_size,
            flush_ms=self.config.batch_flush_ms
        )
        self.circuit = CircuitBreaker(
            failure_threshold=self.config.circuit_failure_threshold,
            timeout_seconds=self.config.circuit_timeout_seconds,
            cooldown_seconds=self.config.circuit_cooldown_seconds
        )
        self.resources = ResourceMonitor(
            max_memory_mb=self.config.max_memory_mb,
            max_connections=self.config.max_connections
        )
        
        # Running flag
        self._running = False
    
    async def initialize(self):
        """Initialize the server."""
        # Initialize connection pool
        db_path = os.path.expanduser(self.config.db_path)
        self.pool = AsyncConnectionPool(db_path, max_connections=self.config.max_workers)
        await self.pool.initialize()
        
        # Initialize database
        from cortex.migrations import run_migrations
        async with self.pool.acquire() as conn:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, run_migrations, conn)
        
        self._running = True
        logger.info("Edge MCP server initialized")
    
    async def cortex_store(
        self,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: str = "[]",
        source: str = "",
        batch: bool = False
    ) -> dict:
        """
        Store a fact (or batch of facts) in CORTEX with optimizations.
        """
        from cortex.engine import CortexEngine
        
        start = time.time()
        
        async with self.pool.acquire() as conn:
            engine = CortexEngine(self.config.db_path, auto_embed=False)
            engine._conn = conn
            
            try:
                if batch:
                    facts = json.loads(content)
                    loop = asyncio.get_event_loop()
                    ids = await loop.run_in_executor(
                        self.executor,
                        engine.store_many,
                        facts
                    )
                    result = {
                        "success": True,
                        "fact_ids": ids,
                        "count": len(ids)
                    }
                else:
                    parsed_tags = json.loads(tags) if tags else []
                    loop = asyncio.get_event_loop()
                    fact_id = await loop.run_in_executor(
                        self.executor,
                        engine.store,
                        project,
                        content,
                        fact_type,
                        parsed_tags,
                        "stated",
                        source or None,
                        None,
                        None
                    )
                    result = {
                        "success": True,
                        "fact_id": fact_id
                    }
                
                # Invalidate cache
                await self.cache.invalidate(f"search:{project}")
                await self.cache.invalidate(f"recall:{project}")
                
                duration_ms = (time.time() - start) * 1000
                self.metrics.record_request("cortex_store", duration_ms)
                
                return result
                
            except Exception as e:
                self.metrics.record_error()
                logger.error("Error in cortex_store: %s", e)
                raise
    
    async def cortex_search(
        self,
        query: str,
        project: str = "",
        top_k: int = 5,
        as_of: str = "",
        use_cache: bool = True
    ) -> dict:
        """Search CORTEX with multi-tier caching."""
        from cortex.engine import CortexEngine
        
        cache_key = self.cache._key(
            "search",
            query=query,
            project=project,
            top_k=top_k,
            as_of=as_of
        )
        
        # Check cache
        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                self.metrics.record_request("cortex_search", 0, cached=True)
                return cached
        
        # Execute search
        start = time.time()
        
        async def _do_search():
            async with self.pool.acquire() as conn:
                engine = CortexEngine(self.config.db_path, auto_embed=False)
                engine._conn = conn
                
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(
                    self.executor,
                    engine.search,
                    query,
                    project or None,
                    top_k,
                    as_of or None
                )
                
                return [
                    {
                        "fact_id": r.fact_id,
                        "project": r.project,
                        "content": r.content[:200] + "..." if len(r.content) > 200 else r.content,
                        "score": r.score,
                        "consensus_score": getattr(r, 'consensus_score', 1.0)
                    }
                    for r in results
                ]
        
        # Use circuit breaker
        results = await self.circuit.call(_do_search)
        
        result = {
            "results": results,
            "count": len(results),
            "query": query
        }
        
        # Cache result
        if use_cache:
            await self.cache.set(cache_key, result)
        
        duration_ms = (time.time() - start) * 1000
        self.metrics.record_request("cortex_search", duration_ms)
        
        return result
    
    async def get_metrics(self) -> dict:
        """Return server metrics."""
        return {
            **self.metrics.get_summary(),
            **self.resources.get_stats()
        }
    
    async def health_check(self) -> dict:
        """Health check endpoint."""
        healthy = self.resources.check_memory()
        
        try:
            async with self.pool.acquire() as conn:
                conn.execute("SELECT 1")
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {e}"
        
        return {
            "status": "healthy" if healthy else "unhealthy",
            "database": db_status,
            "circuit_state": self.circuit.state.value,
            "resources": self.resources.get_stats()
        }
    
    async def close(self):
        """Shutdown the server."""
        self._running = False
        if self.pool:
            await self.pool.close()
        self.executor.shutdown(wait=True)


# Entry point
if __name__ == "__main__":
    import sys
    
    config = EdgeMCPConfig(
        db_path=os.environ.get("CORTEX_DB", "~/.cortex/cortex.db"),
        transport="stdio"
    )
    
    server = EdgeMCPServer(config)
    asyncio.run(server.initialize())
```

### 3.5 Performance Targets

| Metric | Current | Target | Speedup |
|--------|---------|--------|---------|
| Cold search | 50ms | 50ms | — |
| Warm search | 50ms | 1ms | **50x** |
| Batch store (100) | 2300ms | 450ms | **5x** |
| Throughput | 100 req/s | 1000 req/s | **10x** |
| Memory usage | Unbounded | <256MB | **Bounded** |
| P99 latency | Variable | <10ms | **Consistent** |

---

## 4. Deployment Patterns

### 4.1 Docker Deployment

```dockerfile
# Dockerfile.edge
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[edge]"

# Copy application
COPY cortex/ ./cortex/

# Create non-root user
RUN useradd -m -u 1000 cortex && \
    mkdir -p /data && \
    chown -R cortex:cortex /data

# Environment
ENV CORTEX_DB=/data/cortex.db
ENV CORTEX_MAX_MEMORY_MB=256
ENV PYTHONUNBUFFERED=1

USER cortex

# Expose ports
EXPOSE 8484 9999

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8484/health')" || exit 1

# Default: run edge-optimized MCP server
CMD ["python", "-m", "cortex.mcp_server_edge"]
```

### 4.2 Kubernetes Deployment

```yaml
# deploy/k8s-edge-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cortex-edge
  labels:
    app: cortex-edge
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cortex-edge
  template:
    metadata:
      labels:
        app: cortex-edge
    spec:
      containers:
      - name: cortex
        image: cortex:v5.0.0-edge
        ports:
        - containerPort: 8484
          name: api
        - containerPort: 9999
          name: mcp
        env:
        - name: CORTEX_DB
          value: "/data/cortex.db"
        - name: CORTEX_MAX_MEMORY_MB
          value: "256"
        - name: CORTEX_CACHE_TTL
          value: "300"
        resources:
          limits:
            memory: "256Mi"
            cpu: "1000m"
          requests:
            memory: "128Mi"
            cpu: "250m"
        volumeMounts:
        - name: data
          mountPath: /data
        livenessProbe:
          httpGet:
            path: /health
            port: 8484
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8484
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: cortex-edge
spec:
  selector:
    app: cortex-edge
  ports:
  - port: 8484
    targetPort: 8484
    name: api
  - port: 9999
    targetPort: 9999
    name: mcp
  type: ClusterIP
```

### 4.3 Edge Device Deployment (IoT/ARM)

```yaml
# docker-compose.edge.yml
version: "3.8"

services:
  cortex-edge:
    build:
      context: .
      dockerfile: Dockerfile.edge
      platforms:
        - linux/arm64
        - linux/arm/v7
    ports:
      - "8484:8484"
      - "9999:9999"
    volumes:
      - ./data:/data
    environment:
      - CORTEX_DB=/data/cortex.db
      - CORTEX_MAX_MEMORY_MB=128
      - CORTEX_QUERY_CACHE_SIZE=500
      - CORTEX_BATCH_SIZE=50
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.5'
```

---

## 5. Migration Plan

### 5.1 Wave 5 Timeline

```
Week 1-2: Immutable Vote Ledger
├── Migration 010: Vote ledger schema
├── Implementation: VoteLedger class
├── Integration: Hook into vote() method
├── CLI: vote-ledger commands
└── Tests: 95% coverage

Week 3-4: HA Synchronization
├── Migration 011: HA schema (nodes, vector clocks, sync log)
├── Implementation: HASyncManager class
├── Implementation: Raft consensus
├── Implementation: CRDT merge strategies
└── Tests: Multi-node simulation

Week 5-6: Edge MCP Optimization
├── mcp_server_edge.py implementation
├── Multi-tier caching
├── Request batching
├── Circuit breaker
├── Resource monitoring
└── Benchmark suite

Week 7: Deployment
├── Dockerfile.edge
├── docker-compose.edge.yml
├── Kubernetes manifests
├── ARM/IoT builds
└── Documentation

Week 8: Integration & Testing
├── End-to-end HA tests
├── Performance validation
├── Edge deployment tests
├── Security audit
└── Release candidate
```

### 5.2 Migration Commands

```bash
# Upgrade to Wave 5
cortex migrate

# Initialize vote ledger
cortex vote-ledger init

# Create first Merkle checkpoint
cortex vote-ledger checkpoint

# Verify integrity
cortex vote-ledger verify

# Join HA cluster
cortex cluster join --node-id node2 --peers node1:8484

# Start edge-optimized MCP server
cortex mcp start --transport sse --port 9999 --edge-mode

# Run benchmarks
cortex benchmark --suite edge
```

---

## 6. Success Criteria

### 6.1 Technical Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Vote Ledger Verification | <100ms for 10k votes | `cortex vote-ledger verify` |
| HA Failover Time | <5 seconds | Simulated node failure |
| Data Consistency | 100% | Multi-node write/read test |
| MCP Cold Query | <50ms | Benchmark suite |
| MCP Warm Query | <1ms | Benchmark suite |
| MCP Throughput | >1000 req/s | Load test |
| Cache Hit Rate | >80% | Runtime metrics |
| Memory Usage | <256MB | Container metrics |
| Edge Boot Time | <3 seconds | Cold start measurement |

### 6.2 Adoption Metrics

| Metric | Target |
|--------|--------|
| API uptime | 99.9% |
| Error rate | <0.1% |
| Mean recovery time | <5 minutes |
| Vote tamper detection | 100% |
| Consensus consistency | 99.99% |

---

## 7. Security Considerations

### 7.1 Threat Model

| Threat | Mitigation |
|--------|------------|
| Vote tampering | Immutable ledger with Merkle trees |
| Node compromise | Raft consensus requires majority |
| Network partition | CRDT merge strategies |
| Replay attacks | Vector clocks + timestamps |
| Sybil attacks | Reputation-weighted consensus (Wave 4) |
| DoS | Circuit breaker + rate limiting |

### 7.2 Audit Requirements

- All votes cryptographically chained
- Merkle roots for batch verification
- Exportable audit logs
- External anchoring support (optional)
- Tamper detection alerts

---

## Appendix A: API Changes

### New Endpoints

```
POST   /v1/vote-ledger/checkpoint      # Create Merkle checkpoint
GET    /v1/vote-ledger/verify          # Verify vote ledger integrity
POST   /v1/vote-ledger/export          # Export verifiable vote log
GET    /v1/vote-ledger/history/{fact_id} # Get vote history for fact

POST   /v1/cluster/join                # Join HA cluster
POST   /v1/cluster/leave               # Leave HA cluster
GET    /v1/cluster/status              # Get cluster status
GET    /v1/cluster/nodes               # List cluster nodes

GET    /v1/edge/metrics                # Edge server metrics
GET    /v1/edge/health                 # Edge health check
POST   /v1/edge/cache/invalidate       # Invalidate cache
```

### New CLI Commands

```
cortex vote-ledger checkpoint          # Create checkpoint
cortex vote-ledger verify              # Verify integrity
cortex vote-ledger export              # Export log
cortex vote-ledger history <fact_id>   # Get vote history

cortex cluster join                    # Join cluster
cortex cluster leave                   # Leave cluster
cortex cluster status                  # Show cluster status
cortex cluster nodes                   # List nodes

cortex mcp start --edge-mode           # Start edge MCP server
cortex benchmark --suite edge          # Run edge benchmarks
```

---

**End of Wave 5 Proposal**

*Prepared for CORTEX V4.0 Architecture Review | 2026-02-16*

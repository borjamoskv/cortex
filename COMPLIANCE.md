# CORTEX — EU AI Act Compliance Mapping

**Document Version:** 1.0
**Date:** February 20, 2026
**System:** CORTEX Trust Engine v4.3 (BSL-1.1)

---

## Scope

This document maps CORTEX Trust Engine capabilities to the requirements
of the **EU AI Act (Regulation 2024/1689)**, specifically **Article 12**
(Record-Keeping) and related provisions for high-risk AI systems.

**Enforcement Date:** August 2, 2026

---

## Article 12 — Record-Keeping

### Art. 12.1 — Automatic Logging of Events

| Requirement | CORTEX Implementation | Evidence |
|:---|:---|:---|
| High-risk AI systems shall technically allow for the automatic recording of events (logs) | Every `store()` operation creates a transaction in the immutable ledger with SHA-256 hash linking | `cortex/engine/ledger.py` — ImmutableLedger class |
| Logs shall be generated throughout the lifetime of the system | Transaction ledger operates continuously; every fact insertion, update, or deletion is recorded | `transactions` table in cortex.db |

**Verification Command:** `cortex audit-trail`

### Art. 12.2 — Content of Logs

| Requirement | CORTEX Implementation | Evidence |
|:---|:---|:---|
| Recording of the period of each use | `created_at` timestamp on every fact and transaction | `facts.created_at`, `transactions.timestamp` |
| Reference database against which input data has been checked | Project-scoped fact database with full history | `facts.project` scoping |
| Input data for which the search has led to a match | Search results include fact_id, score, and content | `cortex search` / `cortex_search` MCP tool |

### Art. 12.2d — Agent Traceability

| Requirement | CORTEX Implementation | Evidence |
|:---|:---|:---|
| Identification of natural persons involved in verification | Agent tagging system (`agent:xxx` tags on facts) | `facts.tags` field (JSON array) |

**Verification Command:** `cortex compliance-report` (checks agent tracking)

### Art. 12.3 — Tamper-Proof Storage

| Requirement | CORTEX Implementation | Evidence |
|:---|:---|:---|
| Logs shall be kept for an appropriate period of time | Facts are never physically deleted (soft-delete via `valid_until`) | `facts.valid_until` field |
| Logs must be tamper-evident | SHA-256 hash chain: each transaction hash includes the previous hash | `transactions.hash`, `transactions.prev_hash` |
| Integrity must be verifiable | Merkle tree checkpoints enable batch verification | `merkle_roots` table |

**Verification Commands:**
- `cortex verify <fact_id>` — Single fact verification certificate
- `cortex ledger verify` — Full chain integrity check

### Art. 12.4 — Periodic Verification

| Requirement | CORTEX Implementation | Evidence |
|:---|:---|:---|
| Providers shall implement means for periodic integrity verification | Merkle tree checkpoints created at configurable intervals | `ImmutableLedger.create_checkpoint_sync()` |
| Verification results shall be recorded | `integrity_checks` table stores every verification result | `integrity_checks` table (3 checks recorded) |

**Verification Command:** `cortex compliance-report` (runs integrity check)

---

## Additional Compliance Features

### Decision Lineage (Explainability)

CORTEX maintains a `decision_edges` graph that links decisions
chronologically within projects, enabling full chain-of-reasoning
reconstruction.

**Verification Command:** CLI `cortex_decision_lineage` MCP tool

### Multi-Agent Consensus (Art. 14 — Human Oversight)

The Reputation-Weighted Consensus (RWC) system allows multiple agents
to verify facts before they become canonical. This supports human-in-the-loop
oversight requirements.

**Implementation:** `cortex/consensus/` module

### Data Sovereignty (GDPR Art. 22)

CORTEX is 100% local-first (SQLite). No data leaves the deployment
environment. This inherently satisfies data residency and sovereignty
requirements.

---

## Compliance Score

As of February 20, 2026:

```
$ cortex compliance-report

  Compliance Score: 5/5
  🟢 COMPLIANT — All Article 12 requirements met.
```

---

## Limitations

1. **No formal audit:** This mapping has not been reviewed by a certified
   EU AI Act auditor or legal professional.
2. **High-risk classification:** Whether a specific AI system using CORTEX
   qualifies as "high-risk" depends on its use case and sector, not on CORTEX itself.
3. **Organizational measures:** CORTEX provides technical measures only.
   Organizational compliance (policies, training, governance) is the
   responsibility of the deploying organization.

---

**Prepared by:** MOSKV Systems
**Contact:** borja@moskv.dev

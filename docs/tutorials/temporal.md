# Tutorial: Time-Travel Debugging

Use CORTEX's temporal queries to understand what your system knew at any point in time.

## The Problem

Debugging production issues often requires answering: *"What was the configuration when this broke at 3 AM?"* CORTEX stores temporal metadata on every fact, enabling point-in-time recall.

## Store Facts with Temporal Awareness

Every fact gets a `valid_from` timestamp automatically:

```bash
# January 15: store the current rate limit
cortex store my-api "Rate limit: 100 req/min" --type config --tags "rate-limit"

# February 1: update the rate limit (this deprecates the old fact)
cortex edit 1 "Rate limit: 500 req/min"
```

## Query Points in Time

### CLI

```bash
# What did we know on January 20?
cortex history my-api --at "2026-01-20T00:00:00"
# → Shows: "Rate limit: 100 req/min" (was still active)

# What did we know on February 5?
cortex history my-api --at "2026-02-05T00:00:00"
# → Shows: "Rate limit: 500 req/min" (updated version)
```

### Python

```python
from cortex.engine import CortexEngine

engine = CortexEngine()
engine.init_db()

# Current state
current = engine.recall("my-api")

# State as of January 20
january_state = engine.history("my-api", as_of="2026-01-20T00:00:00")
```

### API

```bash
curl http://localhost:8742/recall/my-api?as_of=2026-01-20T00:00:00
```

## Debugging Workflow

1. **Incident occurs** at a specific time
2. **Query CORTEX** for the state at that time:

   ```bash
   cortex history production --at "2026-02-10T03:15:00"
   ```

3. **Compare** with current state:

   ```bash
   cortex recall production
   ```

4. **Identify** what changed between then and now

## Transaction Ledger


Every mutation is recorded in the hash-chained ledger, giving you a complete audit trail:

```python
stats = engine.stats()
print(f"Total transactions: {stats['transactions']}")
```

Each transaction includes:

- **Operation**: `store`, `deprecate`, `edit`
- **Fact ID**: Which fact was affected
- **Hash**: SHA-256 chain for tamper detection
- **Timestamp**: When the operation occurred

## Best Practices

!!! tip "Store configurations as facts"
    When your system configuration changes, store the new values as facts. This creates a history of configuration states that you can query later.

!!! tip "Use fact types for organization"
    - `config` — System configuration values
    - `decision` — Architectural or operational decisions
    - `error` — Known error patterns and their resolutions
    - `knowledge` — General system knowledge

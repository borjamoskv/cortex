# CORTEX cURL Cheatsheet

Quick reference for the CORTEX API. Replace `YOUR_KEY` with your API key.

## Health

```bash
# Health check
curl http://localhost:8000/health

# Metrics
curl http://localhost:8000/metrics
```

## Store Facts

```bash
# Store a knowledge fact
curl -X POST http://localhost:8000/v1/facts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{"content": "CORTEX is a Sovereign Memory Engine.", "type": "knowledge", "project": "demo"}'

# Store a decision
curl -X POST http://localhost:8000/v1/facts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{"content": "Switched to PostgreSQL for production.", "type": "decision", "project": "myapp"}'

# Store an error
curl -X POST http://localhost:8000/v1/facts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{"content": "OOM on batch import >10K facts.", "type": "error", "project": "myapp"}'
```

## Search

```bash
# Semantic search (top 5 results)
curl "http://localhost:8000/v1/search?q=sovereign+memory&top_k=5" \
  -H "X-API-Key: YOUR_KEY"

# Search within a specific project
curl "http://localhost:8000/v1/search?q=database+migration&top_k=3&project=myapp" \
  -H "X-API-Key: YOUR_KEY"
```

## Ask (RAG)

```bash
# Ask a question (requires LLM provider configured)
curl -X POST http://localhost:8000/v1/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{"query": "What errors have occurred in myapp?", "k": 10, "project": "myapp"}'
```

## Admin

```bash
# List all projects
curl http://localhost:8000/v1/projects \
  -H "X-API-Key: YOUR_KEY"

# Export a project
curl "http://localhost:8000/v1/projects/demo/export" \
  -H "X-API-Key: YOUR_KEY"

# LLM provider status
curl http://localhost:8000/v1/llm/status \
  -H "X-API-Key: YOUR_KEY"
```

## Graph

```bash
# Get knowledge graph
curl "http://localhost:8000/v1/graph?project=demo" \
  -H "X-API-Key: YOUR_KEY"
```

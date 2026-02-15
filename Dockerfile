FROM python:3.13-slim

LABEL maintainer="Borja Moskv"
LABEL description="CORTEX — Sovereign Memory Engine for AI Agents"

WORKDIR /app

# System deps for SQLite extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libsqlite3-dev && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY pyproject.toml README.md ./
COPY cortex/ ./cortex/

RUN pip install --no-cache-dir -e ".[api]" && \
    pip install --no-cache-dir sentence-transformers onnxruntime

# Pre-download the embedding model at build time
RUN python -c "from cortex.embeddings import LocalEmbedder; LocalEmbedder()"

# Data volume
VOLUME /data
ENV CORTEX_DB=/data/cortex.db

EXPOSE 8484

HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import httpx; httpx.get('http://localhost:8484/health')" || exit 1

CMD ["uvicorn", "cortex.api:app", "--host", "0.0.0.0", "--port", "8484"]

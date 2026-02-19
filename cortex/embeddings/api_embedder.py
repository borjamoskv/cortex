"""
CORTEX v4.1 — API-based Embedding Engine.

Uses external APIs (Gemini, OpenAI) for embeddings instead of
local ONNX. Useful for cloud deployments where you don't want
to ship a 80MB model.

Environment:
    CORTEX_EMBEDDINGS=api          (enable API mode)
    CORTEX_EMBEDDINGS_PROVIDER=gemini  (or 'openai')
    GEMINI_API_KEY=your-key        (for Gemini)
    OPENAI_API_KEY=your-key        (for OpenAI)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("cortex.embeddings.api")

# ─── Embedding Dimensions ────────────────────────────────────────────
# Must match the local model dimension (384) for compatibility
# or the engine must handle dimension differences.
PROVIDER_CONFIGS = {
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/"
               "text-embedding-004:embedContent",
        "dimension": 768,
        "env_key": "GEMINI_API_KEY",
        "batch_url": "https://generativelanguage.googleapis.com/v1beta/models/"
                     "text-embedding-004:batchEmbedContents",
    },
    "openai": {
        "url": "https://api.openai.com/v1/embeddings",
        "model": "text-embedding-3-small",
        "dimension": 384,  # Can request 384-dim from OpenAI
        "env_key": "OPENAI_API_KEY",
    },
}


class APIEmbedder:
    """Cloud-based embedding engine using external APIs.

    Drop-in replacement for LocalEmbedder. Same .embed() / .embed_batch()
    interface, but calls an API instead of running ONNX locally.
    """

    def __init__(
        self,
        provider: str = "gemini",
        api_key: str | None = None,
        target_dimension: int = 384,
    ):
        if provider not in PROVIDER_CONFIGS:
            raise ValueError(
                f"Unknown provider '{provider}'. "
                f"Supported: {list(PROVIDER_CONFIGS.keys())}"
            )

        self._provider = provider
        self._config = PROVIDER_CONFIGS[provider]
        self._api_key = api_key or os.environ.get(self._config["env_key"], "")
        self._target_dim = target_dimension
        self._client = httpx.AsyncClient(timeout=30.0)

        if not self._api_key:
            raise ValueError(
                f"{self._config['env_key']} is required for {provider} embeddings. "
                f"Set it as an environment variable."
            )

    async def embed(self, text: str | list[str]) -> list[float] | list[list[float]]:
        """Generate embedding(s). Accepts single text or list."""
        if isinstance(text, list):
            return await self.embed_batch(text)

        if not text or not str(text).strip():
            raise ValueError("text cannot be empty")

        if self._provider == "gemini":
            return await self._embed_gemini(str(text))
        elif self._provider == "openai":
            return await self._embed_openai(str(text))

        raise ValueError(f"No embed implementation for {self._provider}")

    async def embed_batch(
        self, texts: list[str], batch_size: int = 32
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []

        if self._provider == "openai":
            return await self._embed_openai_batch(texts)

        # Gemini: sequential for now (batch endpoint available)
        results = []
        for text in texts:
            emb = await self._embed_gemini(text)
            results.append(emb)
        return results

    # ─── Gemini Implementation ────────────────────────────────────

    async def _embed_gemini(self, text: str) -> list[float]:
        """Call Gemini text-embedding-004 API."""
        url = f"{self._config['url']}?key={self._api_key}"
        payload = {
            "content": {"parts": [{"text": text}]},
        }

        response = await self._client.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        values = data.get("embedding", {}).get("values", [])

        # Truncate to target dimension if needed
        if len(values) > self._target_dim:
            values = values[: self._target_dim]

        return values

    # ─── OpenAI Implementation ────────────────────────────────────

    async def _embed_openai(self, text: str) -> list[float]:
        """Call OpenAI embeddings API."""
        result = await self._embed_openai_batch([text])
        return result[0]

    async def _embed_openai_batch(self, texts: list[str]) -> list[list[float]]:
        """Call OpenAI embeddings API with batch support."""
        url = self._config["url"]
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._config["model"],
            "input": texts,
        }
        # OpenAI supports requesting specific dimensions
        if self._target_dim:
            payload["dimensions"] = self._target_dim

        response = await self._client.post(url, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        embeddings = [item["embedding"] for item in data["data"]]
        return embeddings

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._target_dim

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    def __repr__(self) -> str:
        return f"APIEmbedder(provider={self._provider!r}, dim={self._target_dim})"

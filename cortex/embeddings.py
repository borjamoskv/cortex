"""
CORTEX v4.0 — Local Embedding Engine.

Uses sentence-transformers with ONNX Runtime for zero-network-dependency
semantic embeddings. Model auto-downloads on first use (~80MB).

Produces 384-dimensional vectors using all-MiniLM-L6-v2.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger("cortex.embeddings")

# Default model — compact, fast, good quality
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
DEFAULT_CACHE_DIR = Path.home() / ".cortex" / "models"


class LocalEmbedder:
    """Local embedding engine using sentence-transformers.

    Zero network dependencies after first model download.
    Typical latency: ~5-15ms per text on CPU.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        cache_dir: Optional[Path] = None,
    ):
        self._model_name = model_name
        self._cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self._model = None

    def _ensure_model(self):
        """Lazy-load model on first use."""
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model: %s", self._model_name)
            self._model = SentenceTransformer(
                self._model_name,
                cache_folder=str(self._cache_dir),
            )
            logger.info("Model loaded. Dimension: %d", EMBEDDING_DIM)
        except ImportError:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers onnxruntime"
            )

    @lru_cache(maxsize=1024)
    def _embed_cached(self, text: str) -> list[float]:
        """Internal cached embedding for single strings."""
        self._ensure_model()
        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed(self, text: str | list[str]) -> list[float] | list[list[float]]:
        """Generate embedding for a single text or delegate list to batch."""
        if isinstance(text, list):
            return self.embed_batch(text)
            
        if not text or not str(text).strip():
            raise ValueError("text cannot be empty")
            
        return self._embed_cached(str(text))

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
            
        for t in texts:
            if not t or not str(t).strip():
                raise ValueError("embedded text cannot be empty")
                
        self._ensure_model()
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 50,
        )
        return [e.tolist() for e in embeddings]

    @property
    def dimension(self) -> int:
        """Embedding dimension (384 for all-MiniLM-L6-v2)."""
        return EMBEDDING_DIM

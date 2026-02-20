# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v4.2 — LLM Manager.

Lazy-loading singleton for LLM providers. Mirrors the pattern
from EmbeddingManager. Gracefully degrades when no LLM is configured.

    CORTEX_LLM_PROVIDER=""          → No LLM (default)
    CORTEX_LLM_PROVIDER=qwen        → Qwen via DashScope
    CORTEX_LLM_PROVIDER=openrouter  → Any model via OpenRouter
    CORTEX_LLM_PROVIDER=ollama      → Local Ollama
    CORTEX_LLM_PROVIDER=custom      → Any endpoint via CORTEX_LLM_BASE_URL
    ... and 20+ more presets
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("cortex.llm.manager")


class LLMManager:
    """Manages the LLM provider lifecycle.

    Returns None if no provider is configured — CORTEX
    continues to work without LLM (search-only mode).
    """

    def __init__(self):
        self._provider = None
        self._provider_name = os.environ.get("CORTEX_LLM_PROVIDER", "").strip()
        self._initialized = False

    def _get_provider(self):
        """Lazy-load the LLM provider."""
        if self._initialized:
            return self._provider

        self._initialized = True

        if not self._provider_name:
            logger.info("No LLM provider configured (CORTEX_LLM_PROVIDER is empty)")
            return None

        try:
            from cortex.llm.provider import LLMProvider

            self._provider = LLMProvider(provider=self._provider_name)
            logger.info("LLM provider loaded: %s", self._provider)
        except (OSError, RuntimeError, ValueError) as e:
            logger.error(
                "Failed to initialize LLM provider '%s': %s",
                self._provider_name, e,
            )
            self._provider = None

        return self._provider

    @property
    def available(self) -> bool:
        """True if an LLM provider is configured and loaded."""
        return self._get_provider() is not None

    @property
    def provider(self):
        """Get the LLM provider instance (or None)."""
        return self._get_provider()

    @property
    def provider_name(self) -> str:
        """Return the configured provider name (may be empty)."""
        return self._provider_name

    async def complete(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str | None:
        """Complete via the active provider. Returns None if unavailable."""
        p = self._get_provider()
        if p is None:
            return None
        return await p.complete(
            prompt=prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def close(self) -> None:
        """Shut down the provider client."""
        if self._provider is not None:
            await self._provider.close()

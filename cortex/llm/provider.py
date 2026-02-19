# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v4.2 — Universal LLM Provider (OpenAI-compatible).

Async client for ANY OpenAI-compatible LLM endpoint.
Ships with presets for ~20 providers. Any custom endpoint works
via CORTEX_LLM_BASE_URL + CORTEX_LLM_API_KEY + CORTEX_LLM_MODEL.

Environment:
    CORTEX_LLM_PROVIDER=qwen       (preset name, or 'custom')
    CORTEX_LLM_MODEL=override      (optional model override)
    CORTEX_LLM_BASE_URL=https://.. (required if provider='custom')
    CORTEX_LLM_API_KEY=your-key    (required if provider='custom')

    Provider-specific keys (used by presets):
    DASHSCOPE_API_KEY, OPENROUTER_API_KEY, OPENAI_API_KEY,
    ANTHROPIC_API_KEY, GROQ_API_KEY, TOGETHER_API_KEY,
    MISTRAL_API_KEY, DEEPSEEK_API_KEY, FIREWORKS_API_KEY,
    PERPLEXITY_API_KEY, COHERE_API_KEY, ANYSCALE_API_KEY,
    CEREBRAS_API_KEY, SAMBANOVA_API_KEY, XAI_API_KEY,
    GEMINI_API_KEY, DEEPINFRA_API_KEY, LEPTON_API_KEY,
    HYPERBOLIC_API_KEY, NOVITA_API_KEY
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("cortex.llm")


# ─── Provider Presets ─────────────────────────────────────────────────
# Every preset follows OpenAI chat/completions protocol.
# Format: base_url, default_model, env_key, context_window

PROVIDER_PRESETS: dict[str, dict[str, Any]] = {
    # ── Tier 1: Major Cloud Providers ───────────────────────────────
    "qwen": {
        "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "env_key": "DASHSCOPE_API_KEY",
        "context_window": 131072,
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
        "context_window": 128000,
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-sonnet-4-20250514",
        "env_key": "ANTHROPIC_API_KEY",
        "context_window": 200000,
        "extra_headers": {"anthropic-version": "2023-06-01"},
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-2.0-flash",
        "env_key": "GEMINI_API_KEY",
        "context_window": 1000000,
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "mistral-large-latest",
        "env_key": "MISTRAL_API_KEY",
        "context_window": 128000,
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
        "context_window": 128000,
    },
    "xai": {
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-2-latest",
        "env_key": "XAI_API_KEY",
        "context_window": 131072,
    },
    "cohere": {
        "base_url": "https://api.cohere.com/compatibility/v1",
        "default_model": "command-r-plus",
        "env_key": "COHERE_API_KEY",
        "context_window": 128000,
    },

    # ── Tier 2: Inference Platforms & Aggregators ───────────────────
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "qwen/qwen-2.5-72b-instruct",
        "env_key": "OPENROUTER_API_KEY",
        "context_window": 131072,
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
        "context_window": 131072,
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "env_key": "TOGETHER_API_KEY",
        "context_window": 131072,
    },
    "fireworks": {
        "base_url": "https://api.fireworks.ai/inference/v1",
        "default_model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "env_key": "FIREWORKS_API_KEY",
        "context_window": 131072,
    },
    "deepinfra": {
        "base_url": "https://api.deepinfra.com/v1/openai",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct",
        "env_key": "DEEPINFRA_API_KEY",
        "context_window": 131072,
    },
    "anyscale": {
        "base_url": "https://api.endpoints.anyscale.com/v1",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct",
        "env_key": "ANYSCALE_API_KEY",
        "context_window": 131072,
    },
    "perplexity": {
        "base_url": "https://api.perplexity.ai",
        "default_model": "sonar-pro",
        "env_key": "PERPLEXITY_API_KEY",
        "context_window": 200000,
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "default_model": "llama-3.3-70b",
        "env_key": "CEREBRAS_API_KEY",
        "context_window": 131072,
    },
    "sambanova": {
        "base_url": "https://api.sambanova.ai/v1",
        "default_model": "Meta-Llama-3.3-70B-Instruct",
        "env_key": "SAMBANOVA_API_KEY",
        "context_window": 131072,
    },
    "lepton": {
        "base_url": "https://llama3-3-70b.lepton.run/api/v1",
        "default_model": "llama3-3-70b",
        "env_key": "LEPTON_API_KEY",
        "context_window": 131072,
    },
    "hyperbolic": {
        "base_url": "https://api.hyperbolic.xyz/v1",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct",
        "env_key": "HYPERBOLIC_API_KEY",
        "context_window": 131072,
    },
    "novita": {
        "base_url": "https://api.novita.ai/v3/openai",
        "default_model": "meta-llama/llama-3.3-70b-instruct",
        "env_key": "NOVITA_API_KEY",
        "context_window": 131072,
    },

    # ── Tier 3: Local / Self-Hosted ────────────────────────────────
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "default_model": "qwen2.5",
        "env_key": "",
        "context_window": 32768,
    },
    "lmstudio": {
        "base_url": "http://localhost:1234/v1",
        "default_model": "local-model",
        "env_key": "",
        "context_window": 32768,
    },
    "llamacpp": {
        "base_url": "http://localhost:8080/v1",
        "default_model": "local-model",
        "env_key": "",
        "context_window": 32768,
    },
    "vllm": {
        "base_url": "http://localhost:8000/v1",
        "default_model": "local-model",
        "env_key": "",
        "context_window": 32768,
    },
    "jan": {
        "base_url": "http://localhost:1337/v1",
        "default_model": "local-model",
        "env_key": "",
        "context_window": 32768,
    },
}


class LLMProvider:
    """Universal OpenAI-compatible async LLM client.

    Works with ANY endpoint that speaks the OpenAI chat completions
    protocol. Use a preset name or 'custom' with explicit URL/key/model.

    Usage::

        # With preset
        provider = LLMProvider(provider="qwen")

        # Fully custom
        provider = LLMProvider(
            provider="custom",
            base_url="https://my-llm.example.com/v1",
            api_key="sk-...",
            model="my-model-7b",
        )

        answer = await provider.complete("What is CORTEX?")
    """

    def __init__(
        self,
        provider: str = "qwen",
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ):
        # ── Custom endpoint: user provides everything ──────────────
        if provider == "custom":
            self._provider = "custom"
            self._base_url = base_url or os.environ.get("CORTEX_LLM_BASE_URL", "")
            self._model = model or os.environ.get("CORTEX_LLM_MODEL", "custom-model")
            self._api_key = api_key or os.environ.get("CORTEX_LLM_API_KEY", "")
            self._context_window = 32768
            self._extra_headers: dict[str, str] = {}

            if not self._base_url:
                raise ValueError(
                    "Custom provider requires CORTEX_LLM_BASE_URL or base_url parameter."
                )

        # ── Preset endpoint ────────────────────────────────────────
        elif provider in PROVIDER_PRESETS:
            config = PROVIDER_PRESETS[provider]
            self._provider = provider
            self._base_url = base_url or config["base_url"]
            self._model = (
                model
                or os.environ.get("CORTEX_LLM_MODEL", "")
                or config["default_model"]
            )
            self._context_window = config["context_window"]
            self._extra_headers = config.get("extra_headers", {})

            # Resolve API key
            env_key = config["env_key"]
            if env_key:
                self._api_key = api_key or os.environ.get(env_key, "")
                if not self._api_key:
                    raise ValueError(
                        f"{env_key} is required for '{provider}' LLM. "
                        f"Set it as an environment variable."
                    )
            else:
                self._api_key = api_key or ""

        else:
            supported = sorted(list(PROVIDER_PRESETS.keys()) + ["custom"])
            raise ValueError(
                f"Unknown LLM provider '{provider}'. "
                f"Supported: {supported}"
            )

        self._client = httpx.AsyncClient(timeout=60.0)
        logger.info(
            "LLM ready: %s (model=%s, url=%s)",
            self._provider, self._model, self._base_url,
        )

    async def complete(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """Send a chat completion request. Returns the response text.

        Args:
            prompt: The user message / query.
            system: System prompt for context setting.
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens in the response.

        Returns:
            The assistant's response as a string.

        Raises:
            httpx.HTTPStatusError: On API errors (4xx, 5xx).
            ValueError: On unexpected response format.
        """
        url = f"{self._base_url.rstrip('/')}/chat/completions"
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            **self._extra_headers,
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = await self._client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(
                "LLM API error (%s %s): %s",
                e.response.status_code, self._provider,
                e.response.text[:500],
            )
            raise
        except (KeyError, IndexError) as e:
            logger.error("Unexpected LLM response format: %s", e)
            raise ValueError(f"Unexpected response from {self._provider}") from e

    @property
    def model(self) -> str:
        """Active model name."""
        return self._model

    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return self._provider

    @property
    def context_window(self) -> int:
        """Context window in tokens."""
        return self._context_window

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    def __repr__(self) -> str:
        return f"LLMProvider(provider={self._provider!r}, model={self._model!r})"

    @classmethod
    def list_providers(cls) -> list[str]:
        """Return all available preset provider names + 'custom'."""
        return sorted(list(PROVIDER_PRESETS.keys()) + ["custom"])

    @classmethod
    def get_preset_info(cls, provider: str) -> dict[str, Any] | None:
        """Return preset config for a provider, or None if not found."""
        return PROVIDER_PRESETS.get(provider)

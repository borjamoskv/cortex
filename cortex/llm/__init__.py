"""CORTEX v4.2 — LLM Provider Module.

OpenAI-compatible LLM integration for context-aware retrieval.
Supports Qwen (DashScope), OpenRouter, Ollama, and OpenAI.
"""

from cortex.llm.provider import LLMProvider
from cortex.llm.manager import LLMManager

__all__ = ["LLMProvider", "LLMManager"]

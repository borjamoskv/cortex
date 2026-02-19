# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).

"""Tests para CORTEX Thought Orchestra + Fusion."""

from __future__ import annotations

import asyncio
import pytest

from cortex.thinking.fusion import (
    FusedThought,
    FusionStrategy,
    ModelResponse,
    ThoughtFusion,
)
from cortex.thinking.orchestra import (
    OrchestraConfig,
    ThinkingMode,
    ThoughtOrchestra,
    DEFAULT_ROUTING,
)
from cortex.llm.provider import PROVIDER_PRESETS


# ─── Test ModelResponse ──────────────────────────────────────────────


class TestModelResponse:
    def test_ok_when_valid(self):
        r = ModelResponse(provider="openai", model="gpt-4o", content="Hola")
        assert r.ok is True

    def test_not_ok_when_error(self):
        r = ModelResponse(provider="openai", model="gpt-4o", content="", error="timeout")
        assert r.ok is False

    def test_not_ok_when_empty(self):
        r = ModelResponse(provider="openai", model="gpt-4o", content="")
        assert r.ok is False


# ─── Test ThoughtFusion ──────────────────────────────────────────────


class TestThoughtFusion:
    def _make_responses(self, contents: list[str]) -> list[ModelResponse]:
        return [
            ModelResponse(
                provider=f"provider_{i}",
                model=f"model_{i}",
                content=c,
                latency_ms=100.0 * (i + 1),
            )
            for i, c in enumerate(contents)
        ]

    @pytest.mark.asyncio
    async def test_fuse_single_response(self):
        fusion = ThoughtFusion()
        responses = self._make_responses(["La respuesta es 42."])
        result = await fusion.fuse(responses, "¿Cuál es la respuesta?")

        assert isinstance(result, FusedThought)
        assert result.content == "La respuesta es 42."
        assert result.confidence == 0.5  # Single source
        assert result.source_count == 1

    @pytest.mark.asyncio
    async def test_fuse_all_failed(self):
        fusion = ThoughtFusion()
        responses = [
            ModelResponse(provider="a", model="m", content="", error="fail"),
            ModelResponse(provider="b", model="m", content="", error="fail"),
        ]
        result = await fusion.fuse(responses, "test")
        assert result.confidence == 0.0
        assert "error" in result.content.lower() or "fallaron" in result.content.lower()

    @pytest.mark.asyncio
    async def test_fuse_majority_picks_most_central(self):
        fusion = ThoughtFusion()
        responses = self._make_responses([
            "Python es un lenguaje de programación interpretado y dinámico.",
            "Python es un lenguaje de programación de alto nivel interpretado.",
            "JavaScript es un lenguaje de scripting para la web.",
        ])
        result = await fusion.fuse(
            responses, "¿Qué es Python?", strategy=FusionStrategy.MAJORITY
        )
        # Las dos primeras hablan de Python, deberían tener más overlap
        assert "Python" in result.content or "python" in result.content.lower()
        assert result.agreement_score > 0

    @pytest.mark.asyncio
    async def test_agreement_identical_responses(self):
        fusion = ThoughtFusion()
        responses = self._make_responses([
            "La capital de España es Madrid.",
            "La capital de España es Madrid.",
            "La capital de España es Madrid.",
        ])
        agreement = fusion._calculate_agreement(responses)
        assert agreement == 1.0

    @pytest.mark.asyncio
    async def test_agreement_different_responses(self):
        fusion = ThoughtFusion()
        responses = self._make_responses([
            "The quick brown fox jumps over the lazy dog.",
            "Un veloz zorro marrón salta sobre el perro perezoso.",
        ])
        agreement = fusion._calculate_agreement(responses)
        # Diferentes idiomas → bajo overlap
        assert agreement < 0.5

    @pytest.mark.asyncio
    async def test_fuse_synthesis_without_judge_falls_back(self):
        """Sin juez, SYNTHESIS cae a MAJORITY."""
        fusion = ThoughtFusion(judge_provider=None)
        responses = self._make_responses([
            "Respuesta A bastante larga con detalles.",
            "Respuesta B con otra perspectiva interesante.",
        ])
        result = await fusion.fuse(
            responses, "pregunta", strategy=FusionStrategy.SYNTHESIS
        )
        # Debería funcionar con fallback a majority
        assert result.content in [r.content for r in responses]
        assert result.confidence > 0


# ─── Test ThoughtOrchestra Config ────────────────────────────────────


class TestOrchestraConfig:
    def test_default_config(self):
        config = OrchestraConfig()
        assert config.min_models == 2
        assert config.max_models == 5
        assert config.timeout_seconds == 30.0
        assert config.default_strategy == FusionStrategy.SYNTHESIS

    def test_custom_config(self):
        config = OrchestraConfig(min_models=3, max_models=7, timeout_seconds=60)
        assert config.min_models == 3
        assert config.max_models == 7


class TestThoughtOrchestra:
    def test_routing_table_has_all_modes(self):
        for mode in ThinkingMode:
            assert mode.value in DEFAULT_ROUTING or mode in DEFAULT_ROUTING

    def test_thinking_mode_values(self):
        assert ThinkingMode.DEEP_REASONING.value == "deep_reasoning"
        assert ThinkingMode.CODE.value == "code"
        assert ThinkingMode.CREATIVE.value == "creative"
        assert ThinkingMode.SPEED.value == "speed"
        assert ThinkingMode.CONSENSUS.value == "consensus"

    def test_orchestra_creation(self):
        orchestra = ThoughtOrchestra()
        assert orchestra.config.min_models == 2
        assert orchestra._initialized is False

    def test_status_before_init(self):
        orchestra = ThoughtOrchestra()
        status = orchestra.status()
        assert status["initialized"] is False
        assert "modes" in status
        assert "config" in status

    def test_resolve_models_no_keys(self, monkeypatch):
        """Sin API keys configuradas, no hay modelos disponibles."""
        # Limpiar todas las API keys
        for preset in PROVIDER_PRESETS.values():
            env_key = preset.get("env_key", "")
            if env_key:
                monkeypatch.delenv(env_key, raising=False)

        orchestra = ThoughtOrchestra()
        models = orchestra._resolve_models(ThinkingMode.DEEP_REASONING)
        assert len(models) == 0

    def test_resolve_models_with_key(self, monkeypatch):
        """Con API key, el modelo aparece."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key-123")
        # Limpiar las demás
        for name, preset in PROVIDER_PRESETS.items():
            env_key = preset.get("env_key", "")
            if env_key and env_key != "GROQ_API_KEY":
                monkeypatch.delenv(env_key, raising=False)

        orchestra = ThoughtOrchestra()
        models = orchestra._resolve_models(ThinkingMode.SPEED)
        assert len(models) >= 1
        assert ("groq", "llama-3.3-70b-versatile") in models

    @pytest.mark.asyncio
    async def test_think_no_models_returns_error(self, monkeypatch):
        """Sin modelos disponibles, retorna error graceful."""
        for preset in PROVIDER_PRESETS.values():
            env_key = preset.get("env_key", "")
            if env_key:
                monkeypatch.delenv(env_key, raising=False)

        orchestra = ThoughtOrchestra()
        result = await orchestra.think("test", mode="deep_reasoning")
        assert result.confidence == 0.0
        assert "error" in result.content.lower() or "no hay" in result.content.lower()


# ─── Test FusedThought ───────────────────────────────────────────────


class TestFusedThought:
    def test_source_count(self):
        thought = FusedThought(
            content="test",
            strategy=FusionStrategy.MAJORITY,
            confidence=0.8,
            sources=[
                ModelResponse(provider="a", model="m", content="ok"),
                ModelResponse(provider="b", model="m", content="", error="fail"),
                ModelResponse(provider="c", model="m", content="ok2"),
            ],
        )
        assert thought.source_count == 2  # Solo los OK

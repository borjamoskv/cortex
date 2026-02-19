# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).

"""Tests para CORTEX Thought Orchestra + Fusion (MEJORAdo)."""

from __future__ import annotations

import asyncio
import pytest

from cortex.thinking.fusion import (
    FusedThought,
    FusionStrategy,
    ModelResponse,
    ThoughtFusion,
    _tokenize,
    _jaccard,
)
from cortex.thinking.orchestra import (
    OrchestraConfig,
    ThinkingMode,
    ThinkingRecord,
    ThoughtOrchestra,
    DEFAULT_ROUTING,
    MODE_SYSTEM_PROMPTS,
    _ProviderPool,
)
from cortex.llm.provider import PROVIDER_PRESETS


# ─── Helpers ─────────────────────────────────────────────────────────


def _make_responses(contents: list[str], latencies: list[float] | None = None) -> list[ModelResponse]:
    """Factory para crear listas de ModelResponse."""
    if latencies is None:
        latencies = [100.0 * (i + 1) for i in range(len(contents))]
    return [
        ModelResponse(
            provider=f"provider_{i}",
            model=f"model_{i}",
            content=c,
            latency_ms=latencies[i] if i < len(latencies) else 100.0,
        )
        for i, c in enumerate(contents)
    ]


# ─── Test Tokenization ──────────────────────────────────────────────


class TestTokenization:
    def test_tokenize_removes_stopwords(self):
        tokens = _tokenize("The quick brown fox is a very fast animal")
        assert "the" not in tokens
        assert "is" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens
        assert "animal" in tokens

    def test_tokenize_removes_punctuation(self):
        tokens = _tokenize("Hello, world! How are you?")
        assert "hello" in tokens
        assert "world" in tokens
        # "how", "are", "you" son <= 3 chars o stopwords
        assert "," not in tokens
        assert "!" not in tokens

    def test_tokenize_removes_short_tokens(self):
        tokens = _tokenize("I am ok hi no")
        # Todos ≤ 2 chars o stopwords
        assert len(tokens) == 0

    def test_jaccard_identical(self):
        assert _jaccard({"a", "b", "c"}, {"a", "b", "c"}) == 1.0

    def test_jaccard_disjoint(self):
        assert _jaccard({"a", "b"}, {"c", "d"}) == 0.0

    def test_jaccard_partial(self):
        val = _jaccard({"a", "b", "c"}, {"b", "c", "d"})
        assert 0.4 < val < 0.6  # 2/4 = 0.5

    def test_jaccard_empty(self):
        assert _jaccard(set(), set()) == 0.0


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

    def test_label(self):
        r = ModelResponse(provider="openai", model="gpt-4o", content="test")
        assert r.label == "openai:gpt-4o"


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
        assert thought.source_count == 2

    def test_fastest_slowest_source(self):
        thought = FusedThought(
            content="test",
            strategy=FusionStrategy.MAJORITY,
            confidence=0.8,
            sources=_make_responses(["a", "b", "c"], [300.0, 100.0, 200.0]),
        )
        assert thought.fastest_source.latency_ms == 100.0
        assert thought.slowest_source.latency_ms == 300.0

    def test_summary(self):
        thought = FusedThought(
            content="test",
            strategy=FusionStrategy.MAJORITY,
            confidence=0.85,
            agreement_score=0.72,
            sources=_make_responses(["a", "b"], [100.0, 200.0]),
        )
        s = thought.summary()
        assert s["confidence"] == 0.85
        assert s["agreement"] == 0.72
        assert s["sources_ok"] == 2


# ─── Test ThoughtFusion ──────────────────────────────────────────────


class TestThoughtFusion:
    @pytest.mark.asyncio
    async def test_fuse_single_response(self):
        fusion = ThoughtFusion()
        responses = _make_responses(["La respuesta es 42."])
        result = await fusion.fuse(responses, "¿Cuál es la respuesta?")

        assert isinstance(result, FusedThought)
        assert result.content == "La respuesta es 42."
        assert result.confidence == 0.5

    @pytest.mark.asyncio
    async def test_fuse_all_failed(self):
        fusion = ThoughtFusion()
        responses = [
            ModelResponse(provider="a", model="m", content="", error="fail"),
            ModelResponse(provider="b", model="m", content="", error="fail"),
        ]
        result = await fusion.fuse(responses, "test")
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_fuse_majority_picks_most_central(self):
        fusion = ThoughtFusion()
        responses = _make_responses([
            "Python es un lenguaje de programación interpretado y dinámico de alto nivel.",
            "Python es un lenguaje de programación de alto nivel interpretado y potente.",
            "JavaScript es un lenguaje de scripting para desarrollo web frontend.",
        ])
        result = await fusion.fuse(
            responses, "¿Qué es Python?", strategy=FusionStrategy.MAJORITY
        )
        assert "Python" in result.content or "python" in result.content.lower()

    @pytest.mark.asyncio
    async def test_near_identical_early_return(self):
        fusion = ThoughtFusion()
        responses = _make_responses(
            [
                "La capital de España es Madrid.",
                "La capital de España es Madrid.",
                "La capital de España es Madrid.",
            ],
            [300.0, 100.0, 200.0],
        )
        result = await fusion.fuse(responses, "capital?")
        # Debería elegir la más rápida
        assert result.meta.get("near_identical") is True
        assert result.sources[1].latency_ms == 100.0  # fastest

    @pytest.mark.asyncio
    async def test_agreement_identical(self):
        fusion = ThoughtFusion()
        responses = _make_responses([
            "La capital de España es Madrid.",
            "La capital de España es Madrid.",
        ])
        agreement = fusion._calculate_agreement(responses)
        assert agreement == 1.0

    @pytest.mark.asyncio
    async def test_agreement_different_languages(self):
        fusion = ThoughtFusion()
        responses = _make_responses([
            "The quick brown fox jumps over the lazy dog.",
            "Un rápido zorro marrón salta sobre el perro perezoso.",
        ])
        agreement = fusion._calculate_agreement(responses)
        assert agreement < 0.3

    @pytest.mark.asyncio
    async def test_fuse_synthesis_fallback_without_judge(self):
        fusion = ThoughtFusion(judge_provider=None)
        responses = _make_responses([
            "Respuesta A con detalles importantes sobre el tema.",
            "Respuesta B con otra perspectiva relevante y diferente.",
        ])
        result = await fusion.fuse(
            responses, "pregunta", strategy=FusionStrategy.SYNTHESIS
        )
        assert result.content in [r.content for r in responses]
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_weighted_synthesis_strategy_exists(self):
        """Verifica que WEIGHTED_SYNTHESIS es una estrategia válida."""
        assert FusionStrategy.WEIGHTED_SYNTHESIS.value == "weighted_synthesis"


# ─── Test OrchestraConfig ────────────────────────────────────────────


class TestOrchestraConfig:
    def test_default_config(self):
        config = OrchestraConfig()
        assert config.min_models == 2
        assert config.max_models == 5
        assert config.timeout_seconds == 30.0
        assert config.default_strategy == FusionStrategy.SYNTHESIS
        assert config.retry_on_failure is True
        assert config.use_mode_prompts is True

    def test_custom_config(self):
        config = OrchestraConfig(
            min_models=3, max_models=7, timeout_seconds=60,
            retry_on_failure=False,
        )
        assert config.min_models == 3
        assert config.retry_on_failure is False


# ─── Test ProviderPool ───────────────────────────────────────────────


class TestProviderPool:
    def test_pool_size_starts_empty(self):
        pool = _ProviderPool()
        assert pool.size == 0

    @pytest.mark.asyncio
    async def test_pool_close_all_empty(self):
        pool = _ProviderPool()
        await pool.close_all()
        assert pool.size == 0


# ─── Test ThoughtOrchestra ───────────────────────────────────────────


class TestThoughtOrchestra:
    def test_routing_table_has_all_modes(self):
        for mode in ThinkingMode:
            assert mode.value in DEFAULT_ROUTING or mode in DEFAULT_ROUTING

    def test_mode_prompts_has_all_modes(self):
        for mode in ThinkingMode:
            assert mode in MODE_SYSTEM_PROMPTS or mode.value in MODE_SYSTEM_PROMPTS

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
        assert "pool_size" in status
        assert "history_count" in status

    def test_stats_empty(self):
        orchestra = ThoughtOrchestra()
        stats = orchestra.stats()
        assert stats["total_thoughts"] == 0

    def test_resolve_models_no_keys(self, monkeypatch):
        for preset in PROVIDER_PRESETS.values():
            env_key = preset.get("env_key", "")
            if env_key:
                monkeypatch.delenv(env_key, raising=False)

        orchestra = ThoughtOrchestra()
        models = orchestra._resolve_models(ThinkingMode.DEEP_REASONING)
        assert len(models) == 0

    def test_resolve_models_with_key(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key-123")
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
        for preset in PROVIDER_PRESETS.values():
            env_key = preset.get("env_key", "")
            if env_key:
                monkeypatch.delenv(env_key, raising=False)

        orchestra = ThoughtOrchestra()
        result = await orchestra.think("test", mode="deep_reasoning")
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_context_manager(self, monkeypatch):
        for preset in PROVIDER_PRESETS.values():
            env_key = preset.get("env_key", "")
            if env_key:
                monkeypatch.delenv(env_key, raising=False)

        async with ThoughtOrchestra() as o:
            result = await o.think("test")
            assert result.confidence == 0.0
        # Verificar que se cerró
        assert o._pool.size == 0


# ─── Test ThinkingRecord ────────────────────────────────────────────


class TestThinkingRecord:
    def test_record_creation(self):
        record = ThinkingRecord(
            mode="deep_reasoning",
            strategy="synthesis",
            models_queried=5,
            models_succeeded=4,
            total_latency_ms=2500.0,
            confidence=0.85,
            agreement=0.72,
            winner="openai:gpt-4o",
        )
        assert record.mode == "deep_reasoning"
        assert record.timestamp > 0

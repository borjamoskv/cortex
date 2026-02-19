# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v4.3 — Thought Orchestra.

N modelos pensando en paralelo con fusión por consenso.
El cerebro distribuido de CORTEX.

Modos de pensamiento::

    DEEP_REASONING — Modelos top-tier para análisis profundo
    CODE           — Especializados en generación/análisis de código
    CREATIVE       — Para ideación, naming, y pensamiento lateral
    SPEED          — Ultra-rápidos para decisiones instantáneas
    CONSENSUS      — Todos los disponibles para máxima confianza

Uso::

    async with ThoughtOrchestra() as orchestra:
        thought = await orchestra.think("¿Cuál es la raíz del bug?")
        print(thought.content, thought.confidence)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cortex.llm.provider import LLMProvider, PROVIDER_PRESETS
from cortex.thinking.fusion import (
    FusedThought,
    FusionStrategy,
    ModelResponse,
    ThoughtFusion,
)

logger = logging.getLogger("cortex.thinking.orchestra")


# ─── Thinking Modes ──────────────────────────────────────────────────


class ThinkingMode(str, Enum):
    """Modos de pensamiento que determinan qué modelos participan."""

    DEEP_REASONING = "deep_reasoning"
    CODE = "code"
    CREATIVE = "creative"
    SPEED = "speed"
    CONSENSUS = "consensus"


# ─── Mode-specific system prompts ────────────────────────────────────

MODE_SYSTEM_PROMPTS: dict[str, str] = {
    ThinkingMode.DEEP_REASONING: (
        "You are a world-class reasoning AI. Analyze the problem systematically. "
        "Consider multiple angles. Show your reasoning chain. Be thorough."
    ),
    ThinkingMode.CODE: (
        "You are an elite software engineer. Provide clean, production-ready code. "
        "Consider edge cases, performance, and maintainability. Be precise."
    ),
    ThinkingMode.CREATIVE: (
        "You are a brilliant creative thinker. Generate original, unexpected ideas. "
        "Break conventions. Think laterally. Surprise with insight."
    ),
    ThinkingMode.SPEED: (
        "You are a fast, accurate assistant. Give direct, concise answers. "
        "No preamble. Get to the point immediately."
    ),
    ThinkingMode.CONSENSUS: (
        "You are a careful, balanced analyst. Consider all perspectives. "
        "Weigh evidence. Be nuanced and comprehensive."
    ),
}


# ─── Routing Table ───────────────────────────────────────────────────

# modo → lista de (provider, model) a consultar.
# Solo se usarán los que tengan API key configurada.
DEFAULT_ROUTING: dict[str, list[tuple[str, str]]] = {
    ThinkingMode.DEEP_REASONING: [
        ("openai", "gpt-4o"),
        ("anthropic", "claude-sonnet-4-20250514"),
        ("deepseek", "deepseek-reasoner"),
        ("gemini", "gemini-2.0-flash-thinking-exp"),
        ("qwen", "qwen-max"),
    ],
    ThinkingMode.CODE: [
        ("anthropic", "claude-sonnet-4-20250514"),
        ("deepseek", "deepseek-chat"),
        ("qwen", "qwen-coder-plus"),
        ("openai", "gpt-4o"),
        ("fireworks", "accounts/fireworks/models/deepseek-coder-v2"),
    ],
    ThinkingMode.CREATIVE: [
        ("openai", "gpt-4o"),
        ("xai", "grok-2-latest"),
        ("gemini", "gemini-2.0-flash"),
        ("cohere", "command-r-plus"),
        ("qwen", "qwen-plus"),
    ],
    ThinkingMode.SPEED: [
        ("groq", "llama-3.3-70b-versatile"),
        ("cerebras", "llama-3.3-70b"),
        ("sambanova", "Meta-Llama-3.3-70B-Instruct"),
        ("fireworks", "accounts/fireworks/models/llama-v3p3-70b-instruct"),
        ("together", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    ],
    ThinkingMode.CONSENSUS: [
        ("openai", "gpt-4o"),
        ("anthropic", "claude-sonnet-4-20250514"),
        ("deepseek", "deepseek-chat"),
        ("gemini", "gemini-2.0-flash"),
        ("qwen", "qwen-plus"),
        ("groq", "llama-3.3-70b-versatile"),
        ("xai", "grok-2-latest"),
    ],
}


# ─── Configuration ───────────────────────────────────────────────────


@dataclass
class OrchestraConfig:
    """Configuración del orchestra."""

    min_models: int = 2
    max_models: int = 5
    timeout_seconds: float = 30.0
    default_strategy: FusionStrategy = FusionStrategy.SYNTHESIS
    temperature: float = 0.3
    max_tokens: int = 4096
    judge_provider: str | None = None
    judge_model: str | None = None
    # Retry en caso de fallo individual
    retry_on_failure: bool = True
    retry_delay_seconds: float = 1.0
    # Usar system prompts específicos por modo
    use_mode_prompts: bool = True


# ─── Provider Pool ───────────────────────────────────────────────────


class _ProviderPool:
    """Pool de LLMProviders reutilizables.

    Evita crear/destruir httpx.AsyncClient en cada query.
    Un provider por clave (provider_name, model).
    """

    def __init__(self):
        self._pool: dict[tuple[str, str], LLMProvider] = {}

    def get(self, provider_name: str, model: str) -> LLMProvider:
        """Obtiene o crea un provider del pool."""
        key = (provider_name, model)
        if key not in self._pool:
            self._pool[key] = LLMProvider(provider=provider_name, model=model)
            logger.debug("Pool: creado %s:%s", provider_name, model)
        return self._pool[key]

    async def close_all(self) -> None:
        """Cierra todos los providers del pool."""
        for key, provider in self._pool.items():
            try:
                await provider.close()
            except Exception as e:
                logger.debug("Pool: error cerrando %s: %s", key, e)
        self._pool.clear()

    @property
    def size(self) -> int:
        return len(self._pool)


# ─── History Tracking ────────────────────────────────────────────────


@dataclass
class ThinkingRecord:
    """Registro de un pensamiento para análisis retrospectivo."""

    mode: str
    strategy: str
    models_queried: int
    models_succeeded: int
    total_latency_ms: float
    confidence: float
    agreement: float
    winner: str | None = None
    timestamp: float = field(default_factory=time.time)


# ─── Thought Orchestra ──────────────────────────────────────────────


class ThoughtOrchestra:
    """N modelos pensando en paralelo con fusión por consenso.

    Crea instancias de LLMProvider via pool reutilizable.
    Ejecuta en paralelo con asyncio.gather, retry en fallos,
    y fusiona los resultados con ThoughtFusion.

    Soporta context manager::

        async with ThoughtOrchestra() as o:
            result = await o.think("pregunta")
    """

    def __init__(
        self,
        config: OrchestraConfig | None = None,
        routing: dict[str, list[tuple[str, str]]] | None = None,
    ):
        self.config = config or OrchestraConfig()
        self._routing = routing or DEFAULT_ROUTING
        self._pool = _ProviderPool()
        self._fusion: ThoughtFusion | None = None
        self._judge: LLMProvider | None = None
        self._initialized = False
        self._history: list[ThinkingRecord] = []
        self._available_cache: list[str] | None = None

    # ── Lifecycle ────────────────────────────────────────────────

    async def __aenter__(self) -> ThoughtOrchestra:
        self._initialize()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    def _initialize(self) -> None:
        """Lazy initialization: detecta qué providers tienen API key."""
        if self._initialized:
            return

        self._initialized = True
        available = self._detect_available_providers()
        self._available_cache = available

        logger.info(
            "ThoughtOrchestra: %d providers disponibles: %s",
            len(available), available,
        )

        if len(available) < self.config.min_models:
            logger.warning(
                "ThoughtOrchestra necesita mínimo %d providers, hay %d.",
                self.config.min_models, len(available),
            )

        self._judge = self._find_judge(available)
        self._fusion = ThoughtFusion(judge_provider=self._judge)

    @staticmethod
    def _detect_available_providers() -> list[str]:
        """Detecta providers con API key configurada."""
        return [
            name for name, preset in PROVIDER_PRESETS.items()
            if preset.get("env_key") and os.environ.get(preset["env_key"])
        ]

    def _find_judge(self, available: list[str]) -> LLMProvider | None:
        """Encuentra el mejor provider disponible para actuar como juez."""
        # Juez explícito
        judge_name = self.config.judge_provider
        if judge_name and judge_name in available:
            try:
                return self._pool.get(judge_name, self.config.judge_model or "")
            except Exception as e:
                logger.warning("Juez %s no disponible: %s", judge_name, e)

        # Fallback: primer provider premium disponible
        for fallback in ["openai", "anthropic", "gemini", "qwen", "deepseek"]:
            if fallback in available:
                try:
                    return self._pool.get(
                        fallback, PROVIDER_PRESETS[fallback]["default_model"]
                    )
                except Exception:
                    continue
        return None

    # ── Model Resolution ─────────────────────────────────────────

    def _resolve_models(
        self, mode: ThinkingMode | str
    ) -> list[tuple[str, str]]:
        """Resuelve qué modelos usar para un modo dado."""
        mode_key = ThinkingMode(mode) if isinstance(mode, str) else mode
        candidates = self._routing.get(mode_key, [])

        resolved = []
        for provider_name, model in candidates:
            preset = PROVIDER_PRESETS.get(provider_name)
            if not preset:
                continue
            env_key = preset.get("env_key", "")
            if env_key and os.environ.get(env_key):
                resolved.append((provider_name, model))
            if len(resolved) >= self.config.max_models:
                break

        return resolved

    # ── Query with Retry ──────────────────────────────────────────

    async def _query_model(
        self,
        provider_name: str,
        model: str,
        prompt: str,
        system: str,
    ) -> ModelResponse:
        """Consulta un modelo individual con timeout y retry."""
        start = time.monotonic()
        last_error: str | None = None
        attempts = 2 if self.config.retry_on_failure else 1

        for attempt in range(attempts):
            try:
                provider = self._pool.get(provider_name, model)
                content = await asyncio.wait_for(
                    provider.complete(
                        prompt=prompt,
                        system=system,
                        temperature=self.config.temperature,
                        max_tokens=self.config.max_tokens,
                    ),
                    timeout=self.config.timeout_seconds,
                )
                latency = (time.monotonic() - start) * 1000
                return ModelResponse(
                    provider=provider_name,
                    model=model,
                    content=content,
                    latency_ms=latency,
                    token_count=len(content.split()),  # Estimación rough
                )

            except asyncio.TimeoutError:
                last_error = f"Timeout ({self.config.timeout_seconds}s)"
                logger.warning(
                    "%s:%s timeout (intento %d/%d)",
                    provider_name, model, attempt + 1, attempts,
                )
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "%s:%s error (intento %d/%d): %s",
                    provider_name, model, attempt + 1, attempts, e,
                )

            # Esperar antes de retry
            if attempt < attempts - 1:
                await asyncio.sleep(self.config.retry_delay_seconds)

        latency = (time.monotonic() - start) * 1000
        return ModelResponse(
            provider=provider_name,
            model=model,
            content="",
            latency_ms=latency,
            error=last_error,
        )

    # ── Main Think API ────────────────────────────────────────────

    async def think(
        self,
        prompt: str,
        mode: str = "deep_reasoning",
        system: str | None = None,
        strategy: FusionStrategy | str | None = None,
    ) -> FusedThought:
        """Pensamiento multi-modelo con fusión.

        Args:
            prompt: La pregunta o tarea.
            mode: Modo de pensamiento.
            system: System prompt (None = usa el específico del modo).
            strategy: Estrategia de fusión (None = default del config).

        Returns:
            FusedThought con respuesta fusionada, confidence, y metadatos.
        """
        self._initialize()

        models = self._resolve_models(mode)

        if not models:
            logger.error("No hay modelos para modo '%s'.", mode)
            return FusedThought(
                content="Error: no hay modelos disponibles. Configura API keys.",
                strategy=FusionStrategy.MAJORITY,
                confidence=0.0,
            )

        # Resolver system prompt
        if system is None and self.config.use_mode_prompts:
            system = MODE_SYSTEM_PROMPTS.get(mode, MODE_SYSTEM_PROMPTS[ThinkingMode.DEEP_REASONING])
        elif system is None:
            system = "You are a world-class reasoning AI. Think step by step."

        # Resolver estrategia
        if strategy is None:
            fusion_strategy = self.config.default_strategy
        elif isinstance(strategy, str):
            fusion_strategy = FusionStrategy(strategy)
        else:
            fusion_strategy = strategy

        logger.info(
            "🎭 Think [%s] × %d modelos | strategy=%s",
            mode, len(models), fusion_strategy.value,
        )

        # Ejecución paralela
        start = time.monotonic()
        responses = await asyncio.gather(*[
            self._query_model(p, m, prompt, system) for p, m in models
        ])
        total_ms = (time.monotonic() - start) * 1000

        ok_count = sum(1 for r in responses if r.ok)
        logger.info(
            "🎭 Think completado: %.0fms | %d/%d exitosos",
            total_ms, ok_count, len(responses),
        )

        # Fusionar
        result = await self._fusion.fuse(
            responses=list(responses),
            original_prompt=prompt,
            strategy=fusion_strategy,
        )

        # Metadatos del orchestra
        result.meta.update({
            "mode": mode,
            "total_latency_ms": round(total_ms, 1),
            "models_queried": len(models),
            "models_succeeded": ok_count,
            "pool_size": self._pool.size,
        })

        # Registrar en historial
        self._history.append(ThinkingRecord(
            mode=mode,
            strategy=fusion_strategy.value,
            models_queried=len(models),
            models_succeeded=ok_count,
            total_latency_ms=total_ms,
            confidence=result.confidence,
            agreement=result.agreement_score,
            winner=result.meta.get("winner"),
        ))

        return result

    # ── Convenience Methods ───────────────────────────────────────

    async def quick_think(self, prompt: str) -> str:
        """Pensamiento rápido. Retorna solo el contenido."""
        thought = await self.think(prompt, mode="speed", strategy="majority")
        return thought.content

    async def deep_think(self, prompt: str) -> FusedThought:
        """Razonamiento profundo con síntesis."""
        return await self.think(prompt, mode="deep_reasoning", strategy="synthesis")

    async def code_think(self, prompt: str) -> FusedThought:
        """Análisis de código con best-of-n."""
        return await self.think(prompt, mode="code", strategy="best_of_n")

    async def creative_think(self, prompt: str) -> FusedThought:
        """Pensamiento creativo con weighted synthesis."""
        return await self.think(prompt, mode="creative", strategy="weighted_synthesis")

    async def consensus_think(self, prompt: str) -> FusedThought:
        """Máximo consenso — todos los modelos con síntesis."""
        return await self.think(prompt, mode="consensus", strategy="synthesis")

    # ── Cleanup ───────────────────────────────────────────────────

    async def close(self) -> None:
        """Cerrar todas las conexiones del pool."""
        await self._pool.close_all()

    # ── Introspection ────────────────────────────────────────────

    @property
    def available_modes(self) -> list[str]:
        """Modos con al menos 1 modelo configurado."""
        return [m.value for m in ThinkingMode if self._resolve_models(m)]

    @property
    def history(self) -> list[ThinkingRecord]:
        """Historial de pensamientos (más reciente al final)."""
        return self._history

    def status(self) -> dict[str, Any]:
        """Estado completo del orchestra."""
        mode_status = {}
        for mode in ThinkingMode:
            models = self._resolve_models(mode)
            mode_status[mode.value] = {
                "models": [f"{p}:{m}" for p, m in models],
                "count": len(models),
                "ready": len(models) >= self.config.min_models,
            }

        return {
            "initialized": self._initialized,
            "judge": (
                f"{self._judge.provider_name}:{self._judge.model}"
                if self._judge else None
            ),
            "pool_size": self._pool.size,
            "history_count": len(self._history),
            "modes": mode_status,
            "config": {
                "min_models": self.config.min_models,
                "max_models": self.config.max_models,
                "timeout_seconds": self.config.timeout_seconds,
                "default_strategy": self.config.default_strategy.value,
                "retry_on_failure": self.config.retry_on_failure,
                "use_mode_prompts": self.config.use_mode_prompts,
            },
        }

    def stats(self) -> dict[str, Any]:
        """Estadísticas agregadas del historial."""
        if not self._history:
            return {"total_thoughts": 0}

        total = len(self._history)
        avg_confidence = sum(r.confidence for r in self._history) / total
        avg_agreement = sum(r.agreement for r in self._history) / total
        avg_latency = sum(r.total_latency_ms for r in self._history) / total
        success_rate = sum(
            r.models_succeeded / r.models_queried
            for r in self._history if r.models_queried > 0
        ) / total

        # Proveedor que más gana
        winner_counts: dict[str, int] = {}
        for r in self._history:
            if r.winner:
                provider = r.winner.split(":")[0]
                winner_counts[provider] = winner_counts.get(provider, 0) + 1
        top_winner = max(winner_counts, key=winner_counts.get) if winner_counts else None

        return {
            "total_thoughts": total,
            "avg_confidence": round(avg_confidence, 3),
            "avg_agreement": round(avg_agreement, 3),
            "avg_latency_ms": round(avg_latency, 1),
            "model_success_rate": round(success_rate, 3),
            "top_winning_provider": top_winner,
            "mode_distribution": {
                mode: sum(1 for r in self._history if r.mode == mode)
                for mode in {r.mode for r in self._history}
            },
        }

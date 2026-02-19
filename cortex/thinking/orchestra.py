# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v4.3 — Thought Orchestra.

N modelos pensando en paralelo con fusión por consenso.
El cerebro distribuido de CORTEX.

Modos de pensamiento:

    DEEP_REASONING — Modelos top-tier para análisis profundo
    CODE           — Especializados en generación/análisis de código
    CREATIVE       — Para ideación, naming, y pensamiento lateral
    SPEED          — Ultra-rápidos para decisiones instantáneas
    CONSENSUS      — Todos los disponibles para máxima confianza

Uso básico::

    orchestra = ThoughtOrchestra()
    thought = await orchestra.think("¿Cuál es la raíz del bug?", mode="deep_reasoning")
    print(thought.content)       # Respuesta fusionada
    print(thought.confidence)    # 0.0-1.0
    print(thought.sources)       # Respuestas individuales
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


# Routing table: modo → lista de (provider, model) a consultar.
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


@dataclass
class OrchestraConfig:
    """Configuración del orchestra."""

    # Nº mínimo de modelos requeridos para pensar
    min_models: int = 2
    # Nº máximo de modelos a usar (limita costes)
    max_models: int = 5
    # Timeout por modelo en segundos
    timeout_seconds: float = 30.0
    # Estrategia de fusión por defecto
    default_strategy: FusionStrategy = FusionStrategy.SYNTHESIS
    # Temperatura por defecto
    temperature: float = 0.3
    # Max tokens por respuesta
    max_tokens: int = 4096
    # Provider para el juez de síntesis (None = el primero disponible)
    judge_provider: str | None = None
    judge_model: str | None = None


class ThoughtOrchestra:
    """N modelos pensando en paralelo con fusión por consenso.

    Crea instancias de LLMProvider dinámicamente según las API keys
    disponibles. Ejecuta en paralelo con asyncio.gather y fusiona
    los resultados con ThoughtFusion.
    """

    def __init__(
        self,
        config: OrchestraConfig | None = None,
        routing: dict[str, list[tuple[str, str]]] | None = None,
    ):
        self.config = config or OrchestraConfig()
        self._routing = routing or DEFAULT_ROUTING
        self._available_providers: dict[str, LLMProvider] = {}
        self._fusion: ThoughtFusion | None = None
        self._judge: LLMProvider | None = None
        self._initialized = False

    async def _initialize(self) -> None:
        """Lazy initialization: detecta qué providers tienen API key."""
        if self._initialized:
            return

        self._initialized = True

        # Checar qué providers están configurados
        available = []
        for name, preset in PROVIDER_PRESETS.items():
            env_key = preset.get("env_key", "")
            if not env_key:
                continue  # Local providers (ollama, etc.) — no para orchestra
            if os.environ.get(env_key):
                available.append(name)

        logger.info(
            "ThoughtOrchestra: %d providers con API key configurada: %s",
            len(available), available,
        )

        if len(available) < self.config.min_models:
            logger.warning(
                "ThoughtOrchestra necesita mínimo %d providers, solo hay %d. "
                "Configura más API keys para pensamiento multi-modelo.",
                self.config.min_models, len(available),
            )

        # Inicializar el juez para fusión
        judge_provider = self.config.judge_provider
        judge_model = self.config.judge_model
        if judge_provider and judge_provider in available:
            try:
                self._judge = LLMProvider(
                    provider=judge_provider, model=judge_model
                )
            except Exception as e:
                logger.warning("Juez %s no disponible: %s", judge_provider, e)

        # Si no hay juez explícito, usar el primer provider disponible
        if self._judge is None:
            for fallback in ["openai", "anthropic", "gemini", "qwen", "deepseek"]:
                if fallback in available:
                    try:
                        self._judge = LLMProvider(provider=fallback)
                        break
                    except Exception:
                        continue

        self._fusion = ThoughtFusion(judge_provider=self._judge)

    def _resolve_models(
        self, mode: ThinkingMode | str
    ) -> list[tuple[str, str]]:
        """Resuelve qué modelos usar para un modo dado.

        Filtra por API keys disponibles y aplica max_models.
        """
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

    async def _query_model(
        self,
        provider_name: str,
        model: str,
        prompt: str,
        system: str,
    ) -> ModelResponse:
        """Consulta un modelo individual con timeout."""
        start = time.monotonic()
        try:
            # Crear provider fresco (evita problemas de concurrencia)
            provider = LLMProvider(provider=provider_name, model=model)
            try:
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
                )
            finally:
                await provider.close()

        except asyncio.TimeoutError:
            latency = (time.monotonic() - start) * 1000
            logger.warning(
                "%s:%s timeout después de %.0fms", provider_name, model, latency
            )
            return ModelResponse(
                provider=provider_name,
                model=model,
                content="",
                latency_ms=latency,
                error=f"Timeout ({self.config.timeout_seconds}s)",
            )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            logger.error("%s:%s error: %s", provider_name, model, e)
            return ModelResponse(
                provider=provider_name,
                model=model,
                content="",
                latency_ms=latency,
                error=str(e),
            )

    async def think(
        self,
        prompt: str,
        mode: str = "deep_reasoning",
        system: str = "You are a world-class reasoning AI. Think step by step.",
        strategy: FusionStrategy | str | None = None,
    ) -> FusedThought:
        """Pensamiento multi-modelo con fusión.

        Args:
            prompt: La pregunta o tarea.
            mode: Modo de pensamiento (deep_reasoning, code, creative, speed, consensus).
            system: System prompt para todos los modelos.
            strategy: Estrategia de fusión (None = usar default del config).

        Returns:
            FusedThought con respuesta fusionada, confidence, y metadatos.
        """
        await self._initialize()

        # Resolver modelos disponibles para este modo
        models = self._resolve_models(mode)

        if not models:
            logger.error(
                "ThoughtOrchestra: no hay modelos disponibles para modo '%s'. "
                "Configura API keys para los providers del routing.", mode,
            )
            return FusedThought(
                content="Error: no hay modelos disponibles. Configura API keys.",
                strategy=FusionStrategy.MAJORITY,
                confidence=0.0,
            )

        if len(models) == 1:
            logger.info(
                "ThoughtOrchestra: solo 1 modelo disponible (%s). "
                "Se ejecutará sin fusión.", models[0],
            )

        # Resolver estrategia
        if strategy is None:
            fusion_strategy = self.config.default_strategy
        elif isinstance(strategy, str):
            fusion_strategy = FusionStrategy(strategy)
        else:
            fusion_strategy = strategy

        logger.info(
            "🎭 Think [%s] con %d modelos: %s | Strategy: %s",
            mode, len(models),
            [f"{p}:{m}" for p, m in models],
            fusion_strategy.value,
        )

        # Ejecutar TODOS en paralelo
        start = time.monotonic()
        responses = await asyncio.gather(*[
            self._query_model(provider, model, prompt, system)
            for provider, model in models
        ])
        total_ms = (time.monotonic() - start) * 1000

        logger.info(
            "🎭 Think completado en %.0fms | %d/%d exitosos",
            total_ms,
            len([r for r in responses if r.ok]),
            len(responses),
        )

        # Fusionar
        result = await self._fusion.fuse(
            responses=list(responses),
            original_prompt=prompt,
            strategy=fusion_strategy,
        )

        # Agregar metadatos del orchestra
        result.meta["mode"] = mode
        result.meta["total_latency_ms"] = total_ms
        result.meta["models_queried"] = len(models)
        result.meta["models_succeeded"] = len([r for r in responses if r.ok])

        return result

    async def quick_think(self, prompt: str) -> str:
        """Atajo para pensamiento rápido. Retorna solo el contenido."""
        thought = await self.think(prompt, mode="speed", strategy="majority")
        return thought.content

    async def deep_think(self, prompt: str) -> FusedThought:
        """Atajo para razonamiento profundo con síntesis."""
        return await self.think(
            prompt, mode="deep_reasoning", strategy="synthesis"
        )

    async def code_think(self, prompt: str) -> FusedThought:
        """Atajo para análisis de código con best-of-n."""
        return await self.think(
            prompt, mode="code", strategy="best_of_n"
        )

    async def consensus_think(self, prompt: str) -> FusedThought:
        """Máximo consenso — todos los modelos disponibles."""
        return await self.think(
            prompt, mode="consensus", strategy="synthesis"
        )

    async def close(self) -> None:
        """Cerrar todas las conexiones."""
        if self._judge:
            await self._judge.close()

    @property
    def available_modes(self) -> list[str]:
        """Modos disponibles (con al menos 1 modelo configurado)."""
        modes = []
        for mode in ThinkingMode:
            if self._resolve_models(mode):
                modes.append(mode.value)
        return modes

    def status(self) -> dict[str, Any]:
        """Estado del orchestra."""
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
            "modes": mode_status,
            "config": {
                "min_models": self.config.min_models,
                "max_models": self.config.max_models,
                "timeout_seconds": self.config.timeout_seconds,
                "default_strategy": self.config.default_strategy.value,
            },
        }

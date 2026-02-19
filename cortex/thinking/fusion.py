# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v4.3 — Thought Fusion Engine.

Fusiona N respuestas de diferentes modelos en una respuesta
superior. Cuatro estrategias disponibles:

1. MAJORITY: La respuesta más similar al centro del cluster gana.
2. SYNTHESIS: Un modelo-juez fusiona todas las perspectivas.
3. BEST_OF_N: Puntúa cada respuesta en paralelo y elige la mejor.
4. WEIGHTED_SYNTHESIS: Síntesis ponderada por latencia y reputación.
"""

from __future__ import annotations

import asyncio
import json as json_mod
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("cortex.thinking.fusion")

# ─── Constantes ──────────────────────────────────────────────────────

# Palabras demasiado comunes para afectar el agreement
_STOPWORDS = frozenset({
    "the", "is", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "as", "it", "that", "this",
    "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may",
    "might", "can", "not", "no", "so", "if", "then", "than", "more",
    "el", "la", "los", "las", "un", "una", "de", "del", "en", "con",
    "por", "para", "que", "es", "son", "como", "más", "pero", "sin",
})

_PUNCT_RE = re.compile(r"[.,!?;:\"'()\[\]{}—–\-/\\<>@#$%^&*~`|+=]")


# ─── Data Classes ────────────────────────────────────────────────────


class FusionStrategy(str, Enum):
    """Estrategia de fusión de pensamiento."""

    MAJORITY = "majority"
    SYNTHESIS = "synthesis"
    BEST_OF_N = "best_of_n"
    WEIGHTED_SYNTHESIS = "weighted_synthesis"


@dataclass(slots=True)
class ModelResponse:
    """Respuesta de un modelo individual."""

    provider: str
    model: str
    content: str
    latency_ms: float = 0.0
    error: str | None = None
    token_count: int = 0  # Tokens usados (estimación)

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.content)

    @property
    def label(self) -> str:
        """ID legible: 'provider:model'."""
        return f"{self.provider}:{self.model}"


@dataclass(slots=True)
class FusedThought:
    """Resultado de la fusión multi-modelo."""

    content: str
    strategy: FusionStrategy
    confidence: float  # 0.0-1.0
    sources: list[ModelResponse] = field(default_factory=list)
    agreement_score: float = 0.0
    meta: dict = field(default_factory=dict)

    @property
    def source_count(self) -> int:
        return sum(1 for s in self.sources if s.ok)

    @property
    def fastest_source(self) -> ModelResponse | None:
        ok_sources = [s for s in self.sources if s.ok]
        return min(ok_sources, key=lambda s: s.latency_ms) if ok_sources else None

    @property
    def slowest_source(self) -> ModelResponse | None:
        ok_sources = [s for s in self.sources if s.ok]
        return max(ok_sources, key=lambda s: s.latency_ms) if ok_sources else None

    def summary(self) -> dict[str, Any]:
        """Resumen compacto para logging/métricas."""
        return {
            "strategy": self.strategy.value,
            "confidence": round(self.confidence, 3),
            "agreement": round(self.agreement_score, 3),
            "sources_ok": self.source_count,
            "sources_total": len(self.sources),
            "fastest_ms": round(self.fastest_source.latency_ms, 1) if self.fastest_source else None,
            "slowest_ms": round(self.slowest_source.latency_ms, 1) if self.slowest_source else None,
        }


# ─── Tokenización ───────────────────────────────────────────────────


def _tokenize(text: str) -> set[str]:
    """Tokeniza texto en un set de palabras normalizadas.

    Elimina puntuación, stopwords, y tokens muy cortos.
    Reutilizado por _calculate_agreement y _fuse_majority para
    evitar duplicación.
    """
    cleaned = _PUNCT_RE.sub(" ", text.lower())
    return {
        w for w in cleaned.split()
        if len(w) > 2 and w not in _STOPWORDS
    }


def _jaccard(set_a: set[str], set_b: set[str]) -> float:
    """Similitud Jaccard entre dos conjuntos."""
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


# ─── Fusion Engine ───────────────────────────────────────────────────


class ThoughtFusion:
    """Motor de fusión de respuestas multi-modelo.

    Recibe N respuestas y produce una respuesta fusionada
    con confidence score basado en el acuerdo inter-modelo.
    """

    MIN_VALID_RESPONSES = 2

    # ── Prompts del juez ─────────────────────────────────────────

    SYNTHESIS_SYSTEM = (
        "You are a meta-reasoning judge. You receive N responses from "
        "different AI models to the same prompt. Your job is to:\n"
        "1. Identify the strongest insights from EACH response.\n"
        "2. Resolve any contradictions by reasoning about which is correct.\n"
        "3. Synthesize a SINGLE superior response that combines the best parts.\n"
        "4. Be concise but complete. No fluff.\n"
        "Return ONLY the synthesized response, no meta-commentary."
    )

    SCORING_SYSTEM = (
        "You are a response quality evaluator. Rate the following response on:\n"
        "- Accuracy (0-10): Is the information correct?\n"
        "- Completeness (0-10): Does it cover all aspects?\n"
        "- Clarity (0-10): Is it well-structured and clear?\n"
        "- Depth (0-10): Does it go beyond surface-level?\n"
        "Return ONLY a JSON object: "
        '{"accuracy": N, "completeness": N, "clarity": N, "depth": N}'
    )

    WEIGHTED_SYNTHESIS_SYSTEM = (
        "You are a meta-reasoning judge synthesizing AI model responses.\n"
        "Each response has a QUALITY SCORE (0.0-1.0). Higher = more trustworthy.\n"
        "Weight your synthesis toward higher-scored responses, but don't ignore "
        "valid insights from lower-scored ones.\n"
        "Return ONLY the synthesized response."
    )

    # ── High-agreement threshold ─────────────────────────────────

    HIGH_AGREEMENT_THRESHOLD = 0.85
    NEAR_IDENTICAL_THRESHOLD = 0.95

    def __init__(self, judge_provider=None):
        self._judge = judge_provider

    # ── Primary API ──────────────────────────────────────────────

    async def fuse(
        self,
        responses: list[ModelResponse],
        original_prompt: str,
        strategy: FusionStrategy = FusionStrategy.SYNTHESIS,
    ) -> FusedThought:
        """Fusiona N respuestas según la estrategia elegida."""
        valid = [r for r in responses if r.ok]
        failed = [r for r in responses if not r.ok]

        if failed:
            logger.warning(
                "Fusión: %d/%d modelos fallaron: %s",
                len(failed), len(responses),
                [(r.provider, r.error) for r in failed],
            )

        # Sin respuestas válidas
        if not valid:
            return FusedThought(
                content="Error: todos los modelos fallaron.",
                strategy=strategy,
                confidence=0.0,
                sources=responses,
            )

        # Una sola respuesta — no hay nada que fusionar
        if len(valid) == 1:
            return FusedThought(
                content=valid[0].content,
                strategy=strategy,
                confidence=0.5,
                sources=responses,
                agreement_score=1.0,
                meta={"single_source": True, "winner": valid[0].label},
            )

        # Pre-tokenizar (se reutiliza en agreement + majority)
        token_map = {id(r): _tokenize(r.content) for r in valid}

        # Calcular acuerdo
        agreement = self._calculate_agreement_from_tokens(
            [token_map[id(r)] for r in valid]
        )

        # Near-identical → early return con la mejor por latencia
        if agreement > self.NEAR_IDENTICAL_THRESHOLD:
            fastest = min(valid, key=lambda r: r.latency_ms)
            return FusedThought(
                content=fastest.content,
                strategy=FusionStrategy.MAJORITY,
                confidence=min(agreement + 0.05, 1.0),
                sources=responses,
                agreement_score=agreement,
                meta={
                    "winner": fastest.label,
                    "near_identical": True,
                },
            )

        # Alto acuerdo o sin juez → majority
        if (
            agreement > self.HIGH_AGREEMENT_THRESHOLD
            or strategy == FusionStrategy.MAJORITY
            or self._judge is None
        ):
            return self._fuse_majority(valid, responses, agreement, strategy, token_map)

        # Estrategias que requieren juez
        dispatch = {
            FusionStrategy.SYNTHESIS: self._fuse_synthesis,
            FusionStrategy.BEST_OF_N: self._fuse_best_of_n,
            FusionStrategy.WEIGHTED_SYNTHESIS: self._fuse_weighted_synthesis,
        }
        handler = dispatch.get(strategy, self._fuse_synthesis)
        return await handler(valid, responses, original_prompt, agreement)

    # ── Agreement ────────────────────────────────────────────────

    def _calculate_agreement(self, responses: list[ModelResponse]) -> float:
        """Calcula agreement desde ModelResponse (public API)."""
        if len(responses) < 2:
            return 1.0
        token_sets = [_tokenize(r.content) for r in responses]
        return self._calculate_agreement_from_tokens(token_sets)

    @staticmethod
    def _calculate_agreement_from_tokens(token_sets: list[set[str]]) -> float:
        """Jaccard medio entre todos los pares de token sets."""
        if len(token_sets) < 2:
            return 1.0
        similarities = [
            _jaccard(token_sets[i], token_sets[j])
            for i in range(len(token_sets))
            for j in range(i + 1, len(token_sets))
        ]
        return sum(similarities) / len(similarities) if similarities else 0.0

    # ── MAJORITY ─────────────────────────────────────────────────

    def _fuse_majority(
        self,
        valid: list[ModelResponse],
        all_responses: list[ModelResponse],
        agreement: float,
        strategy: FusionStrategy,
        token_map: dict[int, set[str]] | None = None,
    ) -> FusedThought:
        """Elige la respuesta más cercana al 'centro' del cluster.

        Scoring: overlap_promedio × 0.6 + longitud_norm × 0.2 + velocidad_norm × 0.2
        """
        if token_map is None:
            token_map = {id(r): _tokenize(r.content) for r in valid}

        max_latency = max(r.latency_ms for r in valid) or 1.0
        best_score = -1.0
        best_response = valid[0]
        all_scores: dict[str, float] = {}

        for r in valid:
            r_tokens = token_map[id(r)]

            # Overlap medio con las demás
            overlaps = [
                _jaccard(r_tokens, token_map[id(other)])
                for other in valid if other is not r
            ]
            avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0.0

            # Longitud normalizada (cap a 1.0)
            length_score = min(len(r.content) / 2000.0, 1.0)

            # Velocidad normalizada (más rápido = mejor)
            speed_score = 1.0 - (r.latency_ms / max_latency) if max_latency > 0 else 0.5

            score = avg_overlap * 0.6 + length_score * 0.2 + speed_score * 0.2
            all_scores[r.label] = round(score, 4)

            if score > best_score:
                best_score = score
                best_response = r

        return FusedThought(
            content=best_response.content,
            strategy=strategy,
            confidence=min(agreement + 0.2, 1.0),
            sources=all_responses,
            agreement_score=agreement,
            meta={
                "winner": best_response.label,
                "winner_score": round(best_score, 4),
                "all_scores": all_scores,
            },
        )

    # ── SYNTHESIS ─────────────────────────────────────────────────

    async def _fuse_synthesis(
        self,
        valid: list[ModelResponse],
        all_responses: list[ModelResponse],
        original_prompt: str,
        agreement: float,
    ) -> FusedThought:
        """Un modelo-juez fusiona todas las perspectivas."""
        parts = [
            f"=== MODEL {i} ({r.label}, {r.latency_ms:.0f}ms) ===\n{r.content}"
            for i, r in enumerate(valid, 1)
        ]
        judge_prompt = (
            f"ORIGINAL QUESTION:\n{original_prompt}\n\n"
            f"RESPONSES FROM {len(valid)} MODELS:\n\n"
            + "\n\n".join(parts)
        )
        try:
            synthesized = await self._judge.complete(
                prompt=judge_prompt,
                system=self.SYNTHESIS_SYSTEM,
                temperature=0.2,
                max_tokens=4096,
            )
            return FusedThought(
                content=synthesized,
                strategy=FusionStrategy.SYNTHESIS,
                confidence=min(agreement + 0.3, 1.0),
                sources=all_responses,
                agreement_score=agreement,
                meta={"judge": self._judge.provider_name + ":" + self._judge.model},
            )
        except Exception as e:
            logger.error("Juez de síntesis falló: %s — fallback a majority", e)
            return self._fuse_majority(
                valid, all_responses, agreement, FusionStrategy.SYNTHESIS
            )

    # ── BEST_OF_N ─────────────────────────────────────────────────

    async def _fuse_best_of_n(
        self,
        valid: list[ModelResponse],
        all_responses: list[ModelResponse],
        original_prompt: str,
        agreement: float,
    ) -> FusedThought:
        """El juez puntúa cada respuesta EN PARALELO y elige la mejor."""

        async def _score_one(r: ModelResponse) -> tuple[ModelResponse, float]:
            prompt = f"QUESTION: {original_prompt}\n\nRESPONSE:\n{r.content}"
            try:
                raw = await self._judge.complete(
                    prompt=prompt,
                    system=self.SCORING_SYSTEM,
                    temperature=0.0,
                    max_tokens=256,
                )
                # Extraer JSON (tolera markdown code blocks)
                clean = re.sub(r"```json?\s*", "", raw.strip())
                clean = clean.rstrip("`").strip()
                parsed = json_mod.loads(clean)
                total = sum(
                    parsed.get(k, 5) for k in ("accuracy", "completeness", "clarity", "depth")
                ) / 40.0
                return (r, total)
            except Exception as e:
                logger.warning("Scoring falló para %s: %s", r.label, e)
                return (r, 0.5)

        # Paralelo — todos los scorings a la vez
        scored = await asyncio.gather(*[_score_one(r) for r in valid])
        scored_sorted = sorted(scored, key=lambda x: x[1], reverse=True)
        best = scored_sorted[0]

        return FusedThought(
            content=best[0].content,
            strategy=FusionStrategy.BEST_OF_N,
            confidence=best[1],
            sources=all_responses,
            agreement_score=agreement,
            meta={
                "winner": best[0].label,
                "winner_score": round(best[1], 4),
                "all_scores": {r.label: round(s, 4) for r, s in scored_sorted},
            },
        )

    # ── WEIGHTED SYNTHESIS ────────────────────────────────────────

    async def _fuse_weighted_synthesis(
        self,
        valid: list[ModelResponse],
        all_responses: list[ModelResponse],
        original_prompt: str,
        agreement: float,
    ) -> FusedThought:
        """Síntesis ponderada: primero puntúa, luego sintetiza con pesos."""

        # Fase 1: Scoring paralelo (reutiliza _fuse_best_of_n logic)
        async def _quick_score(r: ModelResponse) -> tuple[ModelResponse, float]:
            prompt = f"QUESTION: {original_prompt}\n\nRESPONSE:\n{r.content}"
            try:
                raw = await self._judge.complete(
                    prompt=prompt, system=self.SCORING_SYSTEM,
                    temperature=0.0, max_tokens=256,
                )
                clean = re.sub(r"```json?\s*", "", raw.strip()).rstrip("`").strip()
                parsed = json_mod.loads(clean)
                total = sum(
                    parsed.get(k, 5) for k in ("accuracy", "completeness", "clarity", "depth")
                ) / 40.0
                return (r, total)
            except Exception:
                return (r, 0.5)

        scored = await asyncio.gather(*[_quick_score(r) for r in valid])

        # Fase 2: Síntesis con scores como contexto
        parts = [
            f"=== MODEL {i} (score: {score:.2f}, {r.label}) ===\n{r.content}"
            for i, (r, score) in enumerate(scored, 1)
        ]
        judge_prompt = (
            f"ORIGINAL QUESTION:\n{original_prompt}\n\n"
            f"RESPONSES FROM {len(valid)} MODELS (with quality scores):\n\n"
            + "\n\n".join(parts)
        )
        try:
            synthesized = await self._judge.complete(
                prompt=judge_prompt,
                system=self.WEIGHTED_SYNTHESIS_SYSTEM,
                temperature=0.2,
                max_tokens=4096,
            )
            avg_score = sum(s for _, s in scored) / len(scored)
            return FusedThought(
                content=synthesized,
                strategy=FusionStrategy.WEIGHTED_SYNTHESIS,
                confidence=min(avg_score + 0.2, 1.0),
                sources=all_responses,
                agreement_score=agreement,
                meta={
                    "judge": self._judge.provider_name + ":" + self._judge.model,
                    "all_scores": {r.label: round(s, 4) for r, s in scored},
                },
            )
        except Exception as e:
            logger.error("Weighted synthesis falló: %s — fallback", e)
            # Fallback: elegir la mejor de scoring
            best = max(scored, key=lambda x: x[1])
            return FusedThought(
                content=best[0].content,
                strategy=FusionStrategy.WEIGHTED_SYNTHESIS,
                confidence=best[1],
                sources=all_responses,
                agreement_score=agreement,
                meta={"winner": best[0].label, "fallback": True},
            )

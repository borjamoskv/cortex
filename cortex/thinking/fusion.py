# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v4.3 — Thought Fusion Engine.

Fusiona N respuestas de diferentes modelos en una respuesta
superior. Tres estrategias disponibles:

1. MAJORITY: La respuesta más similar al centro del cluster gana.
2. SYNTHESIS: Un modelo-juez fusiona todas las perspectivas.
3. BEST_OF_N: Puntúa cada respuesta y elige la mejor.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("cortex.thinking.fusion")


class FusionStrategy(str, Enum):
    """Estrategia de fusión de pensamiento."""

    MAJORITY = "majority"
    SYNTHESIS = "synthesis"
    BEST_OF_N = "best_of_n"


@dataclass
class ModelResponse:
    """Respuesta de un modelo individual."""

    provider: str
    model: str
    content: str
    latency_ms: float = 0.0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.content)


@dataclass
class FusedThought:
    """Resultado de la fusión multi-modelo."""

    content: str
    strategy: FusionStrategy
    confidence: float  # 0.0-1.0
    sources: list[ModelResponse] = field(default_factory=list)
    agreement_score: float = 0.0  # Cuánto concuerdan los modelos
    meta: dict = field(default_factory=dict)

    @property
    def source_count(self) -> int:
        return len([s for s in self.sources if s.ok])


class ThoughtFusion:
    """Motor de fusión de respuestas multi-modelo.

    Recibe N respuestas y produce una respuesta fusionada
    con confidence score basado en el acuerdo inter-modelo.
    """

    # Umbral mínimo de respuestas válidas para fusionar
    MIN_VALID_RESPONSES = 2

    # Judge system prompt para síntesis
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
        "- Accuracy (0-10)\n"
        "- Completeness (0-10)\n"
        "- Clarity (0-10)\n"
        "Return ONLY a JSON object: {\"accuracy\": N, \"completeness\": N, \"clarity\": N}"
    )

    def __init__(self, judge_provider=None):
        """
        Args:
            judge_provider: LLMProvider usado como juez para SYNTHESIS y BEST_OF_N.
                          Si None, se usa la estrategia MAJORITY por defecto.
        """
        self._judge = judge_provider

    async def fuse(
        self,
        responses: list[ModelResponse],
        original_prompt: str,
        strategy: FusionStrategy = FusionStrategy.SYNTHESIS,
    ) -> FusedThought:
        """Fusiona N respuestas según la estrategia elegida.

        Args:
            responses: Lista de respuestas de modelos.
            original_prompt: El prompt original para contexto.
            strategy: Estrategia de fusión a usar.

        Returns:
            FusedThought con la respuesta fusionada y metadatos.
        """
        valid = [r for r in responses if r.ok]
        failed = [r for r in responses if not r.ok]

        if failed:
            logger.warning(
                "Fusión: %d/%d modelos fallaron: %s",
                len(failed), len(responses),
                [(r.provider, r.error) for r in failed],
            )

        if len(valid) == 0:
            return FusedThought(
                content="Error: todos los modelos fallaron.",
                strategy=strategy,
                confidence=0.0,
                sources=responses,
            )

        if len(valid) == 1:
            return FusedThought(
                content=valid[0].content,
                strategy=strategy,
                confidence=0.5,  # Confianza media — solo 1 fuente
                sources=responses,
                agreement_score=1.0,
                meta={"single_source": True},
            )

        # Calcular acuerdo textual entre respuestas
        agreement = self._calculate_agreement(valid)

        # Si hay alto acuerdo (>0.85), la mayoría basta
        if agreement > 0.85 or strategy == FusionStrategy.MAJORITY:
            return await self._fuse_majority(valid, responses, agreement, strategy)

        # Para síntesis y best-of-n, necesitamos el juez
        if self._judge is None:
            # Sin juez, fallback a majority
            return await self._fuse_majority(valid, responses, agreement, strategy)

        if strategy == FusionStrategy.SYNTHESIS:
            return await self._fuse_synthesis(
                valid, responses, original_prompt, agreement
            )
        elif strategy == FusionStrategy.BEST_OF_N:
            return await self._fuse_best_of_n(
                valid, responses, original_prompt, agreement
            )

        # Fallback
        return await self._fuse_majority(valid, responses, agreement, strategy)

    def _calculate_agreement(self, responses: list[ModelResponse]) -> float:
        """Calcula el nivel de acuerdo entre respuestas.

        Usa una métrica de similitud simple basada en overlap de tokens.
        Valores: 0.0 (total desacuerdo) a 1.0 (respuestas idénticas).
        """
        if len(responses) < 2:
            return 1.0

        # Tokenizar por palabras (lowercase, sin puntuación corta)
        token_sets = []
        for r in responses:
            tokens = set(
                w.lower().strip(".,!?;:\"'()[]{}") for w in r.content.split()
                if len(w) > 2
            )
            token_sets.append(tokens)

        # Jaccard medio entre todos los pares
        similarities = []
        for i in range(len(token_sets)):
            for j in range(i + 1, len(token_sets)):
                intersection = token_sets[i] & token_sets[j]
                union = token_sets[i] | token_sets[j]
                if union:
                    similarities.append(len(intersection) / len(union))
                else:
                    similarities.append(0.0)

        return sum(similarities) / len(similarities) if similarities else 0.0

    async def _fuse_majority(
        self,
        valid: list[ModelResponse],
        all_responses: list[ModelResponse],
        agreement: float,
        strategy: FusionStrategy,
    ) -> FusedThought:
        """Elige la respuesta más cercana al 'centro' del cluster."""
        # La más larga suele ser la más completa
        # Ponderamos por: longitud normalizada + overlap con otras
        best_score = -1.0
        best_response = valid[0]

        for r in valid:
            r_tokens = set(
                w.lower().strip(".,!?;:\"'()[]{}") for w in r.content.split()
                if len(w) > 2
            )
            # Overlap con TODAS las demás respuestas
            overlap_scores = []
            for other in valid:
                if other is r:
                    continue
                other_tokens = set(
                    w.lower().strip(".,!?;:\"'()[]{}") for w in other.content.split()
                    if len(w) > 2
                )
                union = r_tokens | other_tokens
                if union:
                    overlap_scores.append(len(r_tokens & other_tokens) / len(union))

            avg_overlap = sum(overlap_scores) / len(overlap_scores) if overlap_scores else 0.0
            # Penalizar respuestas demasiado cortas
            length_score = min(len(r.content) / 1000.0, 1.0)
            score = avg_overlap * 0.7 + length_score * 0.3

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
                "winner": f"{best_response.provider}:{best_response.model}",
                "winner_score": best_score,
            },
        )

    async def _fuse_synthesis(
        self,
        valid: list[ModelResponse],
        all_responses: list[ModelResponse],
        original_prompt: str,
        agreement: float,
    ) -> FusedThought:
        """Un modelo-juez fusiona todas las perspectivas."""
        # Construir el prompt para el juez
        parts = []
        for i, r in enumerate(valid, 1):
            parts.append(
                f"=== MODEL {i} ({r.provider}/{r.model}) ===\n{r.content}"
            )

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
                meta={"judge": f"{self._judge.provider_name}:{self._judge.model}"},
            )
        except Exception as e:
            logger.error("Juez de síntesis falló: %s — fallback a majority", e)
            return await self._fuse_majority(
                valid, all_responses, agreement, FusionStrategy.SYNTHESIS
            )

    async def _fuse_best_of_n(
        self,
        valid: list[ModelResponse],
        all_responses: list[ModelResponse],
        original_prompt: str,
        agreement: float,
    ) -> FusedThought:
        """El juez puntúa cada respuesta y elige la mejor."""
        import json as json_mod

        scores: list[tuple[ModelResponse, float]] = []

        for r in valid:
            score_prompt = (
                f"QUESTION: {original_prompt}\n\n"
                f"RESPONSE:\n{r.content}"
            )
            try:
                raw = await self._judge.complete(
                    prompt=score_prompt,
                    system=self.SCORING_SYSTEM,
                    temperature=0.0,
                    max_tokens=256,
                )
                # Extraer JSON
                parsed = json_mod.loads(raw.strip().strip("`").strip("json").strip())
                total = (
                    parsed.get("accuracy", 5)
                    + parsed.get("completeness", 5)
                    + parsed.get("clarity", 5)
                ) / 30.0
                scores.append((r, total))
            except Exception as e:
                logger.warning("Scoring falló para %s: %s", r.provider, e)
                scores.append((r, 0.5))  # Score neutro si falla

        # Elegir el mejor
        scores.sort(key=lambda x: x[1], reverse=True)
        best = scores[0]

        return FusedThought(
            content=best[0].content,
            strategy=FusionStrategy.BEST_OF_N,
            confidence=best[1],
            sources=all_responses,
            agreement_score=agreement,
            meta={
                "winner": f"{best[0].provider}:{best[0].model}",
                "winner_score": best[1],
                "all_scores": {
                    f"{r.provider}:{r.model}": s for r, s in scores
                },
            },
        )

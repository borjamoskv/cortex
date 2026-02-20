"""
CORTEX v4.0 — Context Inference Engine.

Multi-signal triangulation to determine the user's current working context.
Aggregates signals by project, applies weighted scoring, and produces a
confidence-graded inference result.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections import defaultdict
from typing import TYPE_CHECKING

from cortex.context.signals import InferenceResult, Signal

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger("cortex.context")

# Confidence thresholds (ratio of top project score to second)
_CONFIDENCE_MAP = [
    (5.0, "C5"),   # Confirmed — overwhelming evidence
    (3.0, "C4"),   # Probable — strong signal
    (1.5, "C3"),   # Inferred — consistent pattern
    (1.1, "C2"),   # Speculative — weak indicators
    (0.0, "C1"),   # Hypothesis — no clear winner
]


class ContextInference:
    """Infer current working context from collected signals.

    Algorithm:
        1. Group signals by project
        2. Sum weighted scores per project
        3. Rank projects by total score
        4. Compute confidence based on dominance ratio
        5. Generate human-readable summary
    """

    def __init__(self, conn: aiosqlite.Connection | None = None):
        self.conn = conn

    def infer(self, signals: list[Signal]) -> InferenceResult:
        """Run inference on a list of collected signals.

        Args:
            signals: List of Signal objects from ContextCollector.

        Returns:
            InferenceResult with active project, confidence, and explanation.
        """
        if not signals:
            return InferenceResult(
                active_project=None,
                confidence="C1",
                signals_used=0,
                summary="No ambient signals detected. CORTEX is idle.",
                top_signals=[],
                projects_ranked=[],
            )

        # ─── Step 1: Aggregate by project ────────────────────────────
        project_scores: dict[str, float] = defaultdict(float)
        project_signals: dict[str, list[Signal]] = defaultdict(list)
        orphan_signals: list[Signal] = []

        for signal in signals:
            if signal.project:
                project_scores[signal.project] += signal.weight
                project_signals[signal.project].append(signal)
            else:
                orphan_signals.append(signal)

        # ─── Step 2: Rank projects ───────────────────────────────────
        ranked = sorted(project_scores.items(), key=lambda x: x[1], reverse=True)

        if not ranked:
            return InferenceResult(
                active_project=None,
                confidence="C1",
                signals_used=len(signals),
                summary=f"Collected {len(signals)} signals but none mapped to a project.",
                top_signals=signals[:5],
                projects_ranked=[],
            )

        top_project, top_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0

        # ─── Step 3: Compute confidence ──────────────────────────────
        ratio = top_score / second_score if second_score > 0 else float("inf")
        confidence = "C5"
        for threshold, grade in _CONFIDENCE_MAP:
            if ratio >= threshold:
                confidence = grade
                break

        # ─── Step 4: Build summary ───────────────────────────────────
        signal_sources = {s.source.split(":")[0] for s in signals}
        source_str = ", ".join(sorted(signal_sources))

        summary_parts = [
            f"Active project: **{top_project}** (score: {top_score:.2f}).",
            f"Based on {len(signals)} signals from {len(signal_sources)} sources ({source_str}).",
        ]

        if len(ranked) > 1:
            runner_up = ranked[1][0]
            summary_parts.append(
                f"Runner-up: {runner_up} (score: {ranked[1][1]:.2f}, "
                f"ratio: {ratio:.1f}x)."
            )

        # Highlight dominant signal types
        type_counts: dict[str, int] = defaultdict(int)
        for s in project_signals.get(top_project, []):
            type_counts[s.signal_type] += 1
        if type_counts:
            dominant = max(type_counts, key=type_counts.get)
            summary_parts.append(
                f"Dominant signal: {dominant} ({type_counts[dominant]} occurrences)."
            )

        summary = " ".join(summary_parts)

        return InferenceResult(
            active_project=top_project,
            confidence=confidence,
            signals_used=len(signals),
            summary=summary,
            top_signals=signals[:5],
            projects_ranked=ranked,
        )

    async def infer_and_persist(self, signals: list[Signal]) -> InferenceResult:
        """Run inference and persist the result as a context snapshot.

        Requires a database connection (self.conn).
        """
        result = self.infer(signals)

        if self.conn is not None:
            await self._persist_snapshot(result)

        return result

    async def _persist_snapshot(self, result: InferenceResult) -> None:
        """Store inference result in the context_snapshots table."""
        if self.conn is None:
            return

        try:
            await self.conn.execute(
                """
                INSERT INTO context_snapshots
                    (active_project, confidence, signals_used, summary,
                     signals_json, projects_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    result.active_project,
                    result.confidence,
                    result.signals_used,
                    result.summary,
                    json.dumps([s.to_dict() for s in result.top_signals]),
                    json.dumps(
                        [{"project": p, "score": s} for p, s in result.projects_ranked]
                    ),
                ),
            )
            await self.conn.commit()
            logger.debug("Context snapshot persisted (project=%s)", result.active_project)
        except (sqlite3.Error, OSError):
            logger.warning("Failed to persist context snapshot", exc_info=True)

    async def get_history(self, limit: int = 10) -> list[dict]:
        """Retrieve past context snapshots."""
        if self.conn is None:
            return []

        try:
            async with self.conn.execute(
                """
                SELECT id, active_project, confidence, signals_used,
                       summary, signals_json, projects_json, created_at
                FROM context_snapshots
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
        except (sqlite3.Error, OSError):
            logger.debug("Could not read context history", exc_info=True)
            return []

        results = []
        for row in rows:
            signals_data = []
            projects_data = []
            try:
                signals_data = json.loads(row[5]) if row[5] else []
            except (json.JSONDecodeError, TypeError):
                pass
            try:
                projects_data = json.loads(row[6]) if row[6] else []
            except (json.JSONDecodeError, TypeError):
                pass

            results.append({
                "id": row[0],
                "active_project": row[1],
                "confidence": row[2],
                "signals_used": row[3],
                "summary": row[4],
                "top_signals": signals_data,
                "projects_ranked": projects_data,
                "created_at": row[7],
            })

        return results

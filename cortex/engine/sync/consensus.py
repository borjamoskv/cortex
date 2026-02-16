"""Sync Consensus module for CORTEX."""

from __future__ import annotations

import logging

logger = logging.getLogger("cortex.engine.sync.consensus")


class SyncConsensusMixin:
    def vote_sync(self, fact_id: int, agent: str, value: int) -> float:
        """Cast a v1 consensus vote synchronously."""
        if value not in (-1, 0, 1):
            raise ValueError(f"vote value must be -1, 0, or 1, got {value}")
        conn = self._get_sync_conn()
        if value == 0:
            conn.execute(
                "DELETE FROM consensus_votes WHERE fact_id = ? AND agent = ?",
                (fact_id, agent),
            )
        else:
            conn.execute(
                "INSERT OR REPLACE INTO consensus_votes (fact_id, agent, vote) VALUES (?, ?, ?)",
                (fact_id, agent, value),
            )
        # Recalculate consensus score
        row = conn.execute(
            "SELECT SUM(vote) FROM consensus_votes WHERE fact_id = ?",
            (fact_id,),
        ).fetchone()
        vote_sum = row[0] or 0
        score = max(0.0, 1.0 + (vote_sum * 0.1))
        if score >= 1.5:
            conn.execute(
                "UPDATE facts SET consensus_score = ?, confidence = 'verified' WHERE id = ?",
                (score, fact_id),
            )
        elif score <= 0.5:
            conn.execute(
                "UPDATE facts SET consensus_score = ?, confidence = 'disputed' WHERE id = ?",
                (score, fact_id),
            )
        else:
            conn.execute(
                "UPDATE facts SET consensus_score = ? WHERE id = ?",
                (score, fact_id),
            )
        conn.commit()
        return score

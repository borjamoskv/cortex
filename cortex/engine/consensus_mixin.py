"""Consensus mixin — vote, register_agent, vote_v2, consensus recalculation."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from typing import Optional

from cortex.temporal import now_iso

logger = logging.getLogger("cortex")


class ConsensusMixin:
    """Mixin providing consensus/voting methods for CortexEngine."""

    def vote(self, fact_id: int, agent: str, value: int, agent_id: Optional[str] = None) -> float:
        """Cast a consensus vote on a fact."""
        if agent_id:
            return self.vote_v2(fact_id, agent_id, value)

        conn = self._get_conn()
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
        score = self._recalculate_consensus(fact_id, conn)
        conn.commit()
        logger.info("Agent '%s' voted %d on fact #%d (New score: %.2f)", agent, value, fact_id, score)
        return score

    def register_agent(self, name: str, agent_type: str = "ai", public_key: str = "", tenant_id: str = "default") -> str:
        """Register a new agent for Reputation-Weighted Consensus."""
        agent_id = str(uuid.uuid4())
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO agents (id, name, agent_type, public_key, tenant_id) VALUES (?, ?, ?, ?, ?)",
            (agent_id, name, agent_type, public_key, tenant_id),
        )
        conn.commit()
        logger.info("Registered new agent: %s (%s)", name, agent_id)
        return agent_id

    def vote_v2(self, fact_id: int, agent_id: str, value: int, reason: Optional[str] = None) -> float:
        """Cast a reputation-weighted vote (RWC v2)."""
        conn = self._get_conn()
        agent = conn.execute(
            "SELECT reputation_score FROM agents WHERE id = ? AND is_active = 1",
            (agent_id,)
        ).fetchone()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found or inactive")
        rep = agent[0]
        if value == 0:
            conn.execute(
                "DELETE FROM consensus_votes_v2 WHERE fact_id = ? AND agent_id = ?",
                (fact_id, agent_id)
            )
        else:
            conn.execute(
                """
                INSERT OR REPLACE INTO consensus_votes_v2
                (fact_id, agent_id, vote, vote_weight, agent_rep_at_vote, vote_reason)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (fact_id, agent_id, value, rep, rep, reason)
            )
        score = self._recalculate_consensus_v2(fact_id, conn)
        conn.commit()
        return score

    def _recalculate_consensus_v2(self, fact_id: int, conn: sqlite3.Connection) -> float:
        """Calculate consensus score using reputation weights."""
        votes = conn.execute(
            """
            SELECT v.vote, v.vote_weight, a.reputation_score
            FROM consensus_votes_v2 v
            JOIN agents a ON v.agent_id = a.id
            WHERE v.fact_id = ? AND a.is_active = 1
            """,
            (fact_id,)
        ).fetchall()
        if not votes:
            return self._recalculate_consensus(fact_id, conn)
        weighted_sum = 0.0
        total_weight = 0.0
        for vote, vote_weight, current_rep in votes:
            weight = max(vote_weight, current_rep)
            weighted_sum += vote * weight
            total_weight += weight
        if total_weight > 0:
            normalized = weighted_sum / total_weight
            score = 1.0 + normalized
        else:
            score = 1.0
        new_confidence = None
        if score >= 1.6:
            new_confidence = "verified"
        elif score <= 0.4:
            new_confidence = "disputed"
        if new_confidence:
            conn.execute("UPDATE facts SET consensus_score = ?, confidence = ? WHERE id = ?", (score, new_confidence, fact_id))
        else:
            conn.execute("UPDATE facts SET consensus_score = ? WHERE id = ?", (score, fact_id))
        return score

    def _recalculate_consensus(self, fact_id: int, conn: sqlite3.Connection) -> float:
        """Update consensus_score based on votes and adjust confidence."""
        row = conn.execute("SELECT SUM(vote) FROM consensus_votes WHERE fact_id = ?", (fact_id,)).fetchone()
        vote_sum = row[0] or 0
        score = max(0.0, 1.0 + (vote_sum * 0.1))
        new_confidence = None
        if score >= 1.5:
            new_confidence = "verified"
        elif score <= 0.5:
            new_confidence = "disputed"
        if new_confidence:
            conn.execute("UPDATE facts SET consensus_score = ?, confidence = ? WHERE id = ?", (score, new_confidence, fact_id))
        else:
            conn.execute("UPDATE facts SET consensus_score = ? WHERE id = ?", (score, fact_id))
        return score

"""Consensus mixin — vote, register_agent, vote_v2."""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from cortex.metrics import metrics

logger = logging.getLogger("cortex")


class ConsensusMixin:
    async def vote(
        self,
        fact_id: int,
        agent: str,
        value: int,
        agent_id: Optional[str] = None,
    ) -> float:
        """Cast a v1 consensus vote on a fact.

        Args:
            fact_id: The fact to vote on.
            agent: Agent name (v1 style).
            value: Vote value (-1, 0, or 1). 0 removes the vote.
            agent_id: If provided, delegates to vote_v2.
        """
        if agent_id:
            return await self.vote_v2(fact_id, agent_id, value)

        if value not in (-1, 0, 1):
            raise ValueError(f"vote value must be -1, 0, or 1, got {value}")

        conn = await self.get_conn()

        if value == 0:
            await conn.execute(
                "DELETE FROM consensus_votes WHERE fact_id = ? AND agent = ?",
                (fact_id, agent),
            )
            action = "unvote"
        else:
            await conn.execute(
                "INSERT OR REPLACE INTO consensus_votes (fact_id, agent, vote) VALUES (?, ?, ?)",
                (fact_id, agent, value),
            )
            action = "vote"

        await self._log_transaction(
            conn,
            "consensus",
            action,
            {"fact_id": fact_id, "agent": agent, "vote": value},
        )
        score = await self._recalculate_consensus(fact_id, conn)
        await conn.commit()
        return score

    async def register_agent(
        self,
        name: str,
        agent_type: str = "ai",
        public_key: str = "",
        tenant_id: str = "default",
    ) -> str:
        """Register a new agent and return its UUID."""
        agent_id = str(uuid.uuid4())
        conn = await self.get_conn()
        await conn.execute(
            "INSERT INTO agents "
            "(id, name, agent_type, public_key, tenant_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (agent_id, name, agent_type, public_key, tenant_id),
        )
        await conn.commit()
        return agent_id

    async def vote_v2(
        self,
        fact_id: int,
        agent_id: str,
        value: int,
        reason: Optional[str] = None,
    ) -> float:
        """Cast a reputation-weighted consensus vote (v2).

        Args:
            fact_id: The fact to vote on.
            agent_id: UUID of a registered agent.
            value: Vote value (-1, 0, or 1). 0 removes the vote.
            reason: Optional textual justification.
        """
        if value not in (-1, 0, 1):
            raise ValueError(f"vote value must be -1, 0, or 1, got {value}")

        conn = await self.get_conn()
        cursor = await conn.execute(
            "SELECT reputation_score FROM agents WHERE id = ? AND is_active = 1",
            (agent_id,),
        )
        agent = await cursor.fetchone()
        if not agent:
            metrics.inc(
                "cortex_consensus_failures_total",
                labels={"reason": "agent_not_found"},
                meta={"agent_id": agent_id, "fact_id": fact_id},
            )
            raise ValueError(f"Agent {agent_id} not found")

        rep = agent[0]

        if value == 0:
            await conn.execute(
                "DELETE FROM consensus_votes_v2 WHERE fact_id = ? AND agent_id = ?",
                (fact_id, agent_id),
            )
            action = "unvote_v2"
        else:
            await conn.execute(
                "INSERT OR REPLACE INTO consensus_votes_v2 "
                "(fact_id, agent_id, vote, vote_weight, "
                "agent_rep_at_vote, vote_reason) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (fact_id, agent_id, value, rep, rep, reason),
            )
            action = "vote_v2"

        await self._log_transaction(
            conn,
            "consensus",
            action,
            {
                "fact_id": fact_id,
                "agent_id": agent_id,
                "vote": value,
                "rep": rep,
                "reason": reason,
            },
        )
        score = await self._recalculate_consensus_v2(fact_id, conn)
        await conn.commit()
        return score

    async def _recalculate_consensus_v2(self, fact_id: int, conn) -> float:
        """Recalculate consensus using reputation-weighted votes."""
        cursor = await conn.execute(
            "SELECT v.vote, v.vote_weight, a.reputation_score "
            "FROM consensus_votes_v2 v "
            "JOIN agents a ON v.agent_id = a.id "
            "WHERE v.fact_id = ? AND a.is_active = 1",
            (fact_id,),
        )
        votes = await cursor.fetchall()
        if not votes:
            return await self._recalculate_consensus(fact_id, conn)

        weighted_sum = sum(v[0] * max(v[1], v[2]) for v in votes)
        total_weight = sum(max(v[1], v[2]) for v in votes)
        score = 1.0 + (weighted_sum / total_weight) if total_weight > 0 else 1.0
        await self._update_fact_score(fact_id, score, conn)
        return score

    async def _recalculate_consensus(self, fact_id: int, conn) -> float:
        """Recalculate consensus from simple v1 votes."""
        cursor = await conn.execute(
            "SELECT SUM(vote) FROM consensus_votes WHERE fact_id = ?",
            (fact_id,),
        )
        row = await cursor.fetchone()
        vote_sum = row[0] or 0
        score = max(0.0, 1.0 + (vote_sum * 0.1))
        await self._update_fact_score(fact_id, score, conn)
        return score

    async def _update_fact_score(self, fact_id: int, score: float, conn) -> None:
        """Update fact consensus score and auto-set confidence."""
        if score >= 1.5:
            conf = "verified"
        elif score <= 0.5:
            conf = "disputed"
        else:
            conf = None

        if conf:
            await conn.execute(
                "UPDATE facts SET consensus_score = ?, confidence = ? WHERE id = ?",
                (score, conf, fact_id),
            )
        else:
            await conn.execute(
                "UPDATE facts SET consensus_score = ? WHERE id = ?",
                (score, fact_id),
            )

""" Consensus mixin — vote, register_agent, vote_v2. """
from __future__ import annotations
import logging
import sqlite3
import uuid
from typing import Optional

logger = logging.getLogger("cortex")

class ConsensusMixin:
    def vote(self, fact_id: int, agent: str, value: int, agent_id: Optional[str] = None) -> float:
        if agent_id: return self.vote_v2(fact_id, agent_id, value)
        conn = self._get_conn()
        if value == 0: conn.execute("DELETE FROM consensus_votes WHERE fact_id = ? AND agent = ?", (fact_id, agent))
        else: conn.execute("INSERT OR REPLACE INTO consensus_votes (fact_id, agent, vote) VALUES (?, ?, ?)", (fact_id, agent, value))
        score = self._recalculate_consensus(fact_id, conn)
        conn.commit()
        return score

    def register_agent(self, name: str, agent_type: str = "ai", public_key: str = "", tenant_id: str = "default") -> str:
        agent_id = str(uuid.uuid4()); conn = self._get_conn()
        conn.execute("INSERT INTO agents (id, name, agent_type, public_key, tenant_id) VALUES (?, ?, ?, ?, ?)", (agent_id, name, agent_type, public_key, tenant_id))
        conn.commit(); return agent_id

    def vote_v2(self, fact_id: int, agent_id: str, value: int, reason: Optional[str] = None) -> float:
        conn = self._get_conn()
        agent = conn.execute("SELECT reputation_score FROM agents WHERE id = ? AND is_active = 1", (agent_id,)).fetchone()
        if not agent: raise ValueError(f"Agent {agent_id} not found")
        rep = agent[0]
        if value == 0: conn.execute("DELETE FROM consensus_votes_v2 WHERE fact_id = ? AND agent_id = ?", (fact_id, agent_id))
        else: conn.execute("INSERT OR REPLACE INTO consensus_votes_v2 (fact_id, agent_id, vote, vote_weight, agent_rep_at_vote, vote_reason) VALUES (?, ?, ?, ?, ?, ?)", (fact_id, agent_id, value, rep, rep, reason))
        score = self._recalculate_consensus_v2(fact_id, conn)
        conn.commit(); return score

    def _recalculate_consensus_v2(self, fact_id: int, conn: sqlite3.Connection) -> float:
        votes = conn.execute("SELECT v.vote, v.vote_weight, a.reputation_score FROM consensus_votes_v2 v JOIN agents a ON v.agent_id = a.id WHERE v.fact_id = ? AND a.is_active = 1", (fact_id,)).fetchall()
        if not votes: return self._recalculate_consensus(fact_id, conn)
        weighted_sum = sum(v[0] * max(v[1], v[2]) for v in votes)
        total_weight = sum(max(v[1], v[2]) for v in votes)
        score = 1.0 + (weighted_sum / total_weight) if total_weight > 0 else 1.0
        self._update_fact_score(fact_id, score, conn); return score

    def _recalculate_consensus(self, fact_id: int, conn: sqlite3.Connection) -> float:
        row = conn.execute("SELECT SUM(vote) FROM consensus_votes WHERE fact_id = ?", (fact_id,)).fetchone()
        vote_sum = row[0] or 0; score = max(0.0, 1.0 + (vote_sum * 0.1))
        self._update_fact_score(fact_id, score, conn); return score

    def _update_fact_score(self, fact_id: int, score: float, conn: sqlite3.Connection):
        conf = "verified" if score >= 1.5 else "disputed" if score <= 0.5 else None
        if conf: conn.execute("UPDATE facts SET consensus_score = ?, confidence = ? WHERE id = ?", (score, conf, fact_id))
        else: conn.execute("UPDATE facts SET consensus_score = ? WHERE id = ?", (score, fact_id))

"""Agent management mixin."""
import uuid
import aiosqlite
from typing import Optional, Dict, Any, List

class AgentMixin:
    """Mixin for agent management operations."""

    async def register_agent(self, name: str, agent_type: str = "ai", public_key: str = "", tenant_id: str = "default") -> str:
        agent_id = str(uuid.uuid4())
        async with self.session() as conn:
            await conn.execute("BEGIN IMMEDIATE")
            try:
                await conn.execute(
                    "INSERT INTO agents (id, name, agent_type, public_key, tenant_id) VALUES (?, ?, ?, ?, ?)",
                    (agent_id, name, agent_type, public_key, tenant_id)
                )
                await conn.commit()
                return agent_id
            except Exception as e:
                await conn.rollback()
                raise e

    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        async with self.session() as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT id, name, agent_type, reputation_score, created_at FROM agents WHERE id = ?", (agent_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def list_agents(self, tenant_id: str) -> List[Dict[str, Any]]:
        async with self.session() as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT id, name, agent_type, reputation_score, created_at FROM agents WHERE tenant_id = ?", (tenant_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

"""
CORTEX Memory Client for Open-Antigravity Orchestrator.

This module provides a typed Python client that the Open-Antigravity
Gateway/Orchestrator uses to interact with the CORTEX Memory Engine.

Usage:
    from cortex_client import CortexMemoryClient

    client = CortexMemoryClient(base_url="http://cortex-memory:8484")
    await client.store_decision("my-project", "Chose React over Vue for UI")
    results = await client.search("authentication architecture", k=5)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx


CORTEX_DEFAULT_URL = os.getenv("CORTEX_URL", "http://localhost:8484")
CORTEX_API_KEY = os.getenv("CORTEX_API_KEY", "")


@dataclass
class CortexFact:
    """A single fact from CORTEX memory."""

    id: int
    project: str
    fact_type: str
    content: str
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    deprecated: bool = False


@dataclass
class SearchResult:
    """A search result with similarity score."""

    fact: CortexFact
    score: float
    source: str = "vector"


class CortexMemoryClient:
    """
    Async client for CORTEX Memory Engine.

    Designed to be used by the Open-Antigravity Orchestrator to provide
    persistent memory, semantic search, and multi-agent consensus to all
    agents in the system.
    """

    def __init__(
        self,
        base_url: str = CORTEX_DEFAULT_URL,
        api_key: str = CORTEX_API_KEY,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self._headers = {}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=timeout,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> CortexMemoryClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ─── Health ──────────────────────────────────────────────────────

    async def health(self) -> dict[str, Any]:
        """Check CORTEX service health."""
        resp = await self._client.get("/health")
        resp.raise_for_status()
        return resp.json()

    async def is_alive(self) -> bool:
        """Quick liveness check."""
        try:
            data = await self.health()
            return data.get("status") == "healthy"
        except (httpx.HTTPError, Exception):
            return False

    # ─── Facts (Store & Recall) ──────────────────────────────────────

    async def store_fact(
        self,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Store a fact in CORTEX memory."""
        payload = {
            "project": project,
            "content": content,
            "type": fact_type,
        }
        if tags:
            payload["tags"] = ",".join(tags)
        resp = await self._client.post("/v1/facts", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def store_decision(
        self, project: str, content: str, tags: list[str] | None = None
    ) -> dict[str, Any]:
        """Store a decision (convenience wrapper)."""
        return await self.store_fact(project, content, "decision", tags)

    async def store_error(
        self, project: str, content: str, tags: list[str] | None = None
    ) -> dict[str, Any]:
        """Store an error for future reference."""
        return await self.store_fact(project, content, "error", tags)

    async def store_ghost(
        self, project: str, content: str, tags: list[str] | None = None
    ) -> dict[str, Any]:
        """Store a ghost (incomplete work marker)."""
        return await self.store_fact(project, content, "ghost", tags)

    async def recall(
        self, project: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Recall all facts for a project."""
        resp = await self._client.get(
            f"/v1/projects/{project}/facts", params={"limit": limit}
        )
        resp.raise_for_status()
        return resp.json()

    # ─── Search ──────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        k: int = 5,
        include_graph: bool = False,
        graph_depth: int = 0,
    ) -> list[dict[str, Any]]:
        """Semantic search across all CORTEX memory."""
        payload = {
            "query": query,
            "k": k,
            "include_graph": include_graph,
            "graph_depth": graph_depth,
        }
        resp = await self._client.post("/v1/search", json=payload)
        resp.raise_for_status()
        return resp.json()

    # ─── Ask (RAG) ───────────────────────────────────────────────────

    async def ask(self, question: str, k: int = 5) -> dict[str, Any]:
        """RAG endpoint: search → synthesize → answer."""
        payload = {"question": question, "k": k}
        resp = await self._client.post("/v1/ask", json=payload)
        resp.raise_for_status()
        return resp.json()

    # ─── Consensus ───────────────────────────────────────────────────

    async def dispatch_mission(
        self,
        mission: str,
        agents: list[str] | None = None,
        formation: str = "IRON_DOME",
    ) -> dict[str, Any]:
        """Dispatch a consensus mission to the agent swarm."""
        payload = {
            "mission": mission,
            "formation": formation,
        }
        if agents:
            payload["agents"] = agents
        resp = await self._client.post("/v1/missions/dispatch", json=payload)
        resp.raise_for_status()
        return resp.json()

    # ─── Admin ───────────────────────────────────────────────────────

    async def status(self) -> dict[str, Any]:
        """Get CORTEX engine status and statistics."""
        resp = await self._client.get("/v1/status")
        resp.raise_for_status()
        return resp.json()

    async def create_api_key(
        self, name: str, tenant_id: str = "default"
    ) -> dict[str, Any]:
        """Create a new API key for a workspace/tenant."""
        resp = await self._client.post(
            "/v1/admin/keys",
            params={"name": name, "tenant_id": tenant_id},
        )
        resp.raise_for_status()
        return resp.json()

    # ─── Agent Lifecycle Hooks ───────────────────────────────────────

    async def on_agent_start(
        self, agent_id: str, project: str, task: str
    ) -> None:
        """Called when an agent starts a task. Injects relevant context."""
        context = await self.search(task, k=10)
        # The orchestrator should inject these results into the agent prompt
        return context

    async def on_agent_complete(
        self, agent_id: str, project: str, summary: str, decisions: list[str]
    ) -> None:
        """Called when an agent completes. Persists learnings."""
        for decision in decisions:
            await self.store_decision(
                project, decision, tags=[f"agent:{agent_id}"]
            )
        await self.store_fact(
            project,
            f"Agent {agent_id} completed: {summary}",
            "knowledge",
            tags=[f"agent:{agent_id}", "completion"],
        )

    async def on_agent_error(
        self, agent_id: str, project: str, error: str
    ) -> None:
        """Called when an agent encounters an error. Persists for learning."""
        await self.store_error(
            project, f"Agent {agent_id} error: {error}",
            tags=[f"agent:{agent_id}", "error"],
        )

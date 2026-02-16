"""
CORTEX v4.0 — Python SDK Client.

Simple, ergonomic client for the CORTEX REST API.

Usage:
    from cortex.client import CortexClient

    client = CortexClient("http://localhost:8484", api_key="ctx_...")
    client.store("my-project", "Important fact about the system")
    results = client.search("what is important?")
"""

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class Fact:
    """A single fact from CORTEX."""

    id: int
    project: str
    content: str
    fact_type: str
    tags: list[str]
    created_at: str
    valid_from: str
    valid_until: str | None = None
    score: float = 0.0


class CortexError(Exception):
    """Base error for CORTEX client."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"CORTEX API error {status_code}: {detail}")


class CortexClient:
    """Python SDK for the CORTEX Sovereign Memory API.

    Args:
        base_url: API server URL (default: http://localhost:8484)
        api_key: API key (or set CORTEX_API_KEY env var)
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8484",
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("CORTEX_API_KEY", "")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._headers(),
        )

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _request(self, method: str, path: str, **kwargs) -> dict:
        resp = self._client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            detail = (
                resp.json().get("detail", resp.text)
                if resp.headers.get("content-type", "").startswith("application/json")
                else resp.text
            )
            raise CortexError(resp.status_code, detail)
        return resp.json()

    # ─── Facts ────────────────────────────────────────────────────────

    def store(
        self,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: list[str] | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Store a fact. Returns fact ID."""
        data = {
            "project": project,
            "content": content,
            "fact_type": fact_type,
            "tags": tags or [],
        }
        if metadata:
            data["metadata"] = metadata
        result = self._request("POST", "/v1/facts", json=data)
        return result["fact_id"]

    def search(
        self,
        query: str,
        k: int = 5,
        project: str | None = None,
    ) -> list[Fact]:
        """Semantic search. Returns ranked facts."""
        data: dict[str, Any] = {"query": query, "k": k}
        if project:
            data["project"] = project
        results = self._request("POST", "/v1/search", json=data)
        return [
            Fact(
                id=r["fact_id"],
                project=r["project"],
                content=r["content"],
                fact_type=r["fact_type"],
                tags=r.get("tags", []),
                created_at="",
                valid_from="",
                score=r.get("score", 0.0),
            )
            for r in results
        ]

    def recall(self, project: str, include_deprecated: bool = False) -> list[Fact]:
        """Get all facts for a project."""
        params = {"include_deprecated": str(include_deprecated).lower()}
        results = self._request("GET", f"/v1/projects/{project}/facts", params=params)
        return [
            Fact(
                id=f["id"],
                project=f["project"],
                content=f["content"],
                fact_type=f["fact_type"],
                tags=f.get("tags", []),
                created_at=f.get("created_at", ""),
                valid_from=f.get("valid_from", ""),
                valid_until=f.get("valid_until"),
            )
            for f in results
        ]

    def deprecate(self, fact_id: int) -> bool:
        """Deprecate a fact (soft delete)."""
        self._request("DELETE", f"/v1/facts/{fact_id}")
        return True

    def status(self) -> dict:
        """Get engine status."""
        return self._request("GET", "/v1/status")

    # ─── Admin ────────────────────────────────────────────────────────

    def create_key(self, name: str, tenant_id: str = "default") -> dict:
        """Create a new API key (admin only)."""
        return self._request(
            "POST", "/v1/admin/keys", params={"name": name, "tenant_id": tenant_id}
        )

    def list_keys(self) -> list[dict]:
        """List all API keys (admin only)."""
        return self._request("GET", "/v1/admin/keys")

    # ─── Context Manager ──────────────────────────────────────────────

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

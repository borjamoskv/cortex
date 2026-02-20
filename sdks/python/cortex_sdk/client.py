"""
CORTEX SDK Client — Zero-dependency HTTP client for CORTEX API.

Supports all core operations: store, search, recall, verify, graph.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Fact:
    """A single fact returned from CORTEX."""
    id: int
    project: str
    content: str
    fact_type: str = "general"
    tags: list[str] = field(default_factory=list)
    confidence: str = "medium"
    score: float | None = None
    created_at: str | None = None
    tx_id: int | None = None
    hash: str | None = None
    context: dict | None = None


@dataclass
class LedgerReport:
    """Cryptographic ledger verification result."""
    valid: bool
    violations: list[str] = field(default_factory=list)
    tx_checked: int = 0
    roots_checked: int = 0
    votes_checked: int = 0


class CortexError(Exception):
    """Base exception for CORTEX SDK errors."""
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(f"[{status}] {message}")


class Cortex:
    """
    Thin client for the CORTEX Memory API.

    Args:
        base_url: CORTEX API server URL (e.g. "http://localhost:8000")
        api_key: API key for authentication (header: X-API-Key)
        timeout: Request timeout in seconds (default: 30)

    Example:
        >>> ctx = Cortex("http://localhost:8000", api_key="sk-12345")
        >>> ctx.store("user likes techno", project="music")
        42
        >>> ctx.search("what music?", top_k=3)
        [Fact(id=42, content='user likes techno', ...)]
    """

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = "", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    # ── Core Operations ────────────────────────────────────────

    def store(
        self,
        content: str,
        *,
        project: str = "default",
        fact_type: str = "general",
        tags: list[str] | None = None,
        source: str | None = None,
        meta: dict | None = None,
    ) -> int:
        """
        Store a fact in CORTEX.

        Returns:
            The fact ID of the stored fact.
        """
        body: dict[str, Any] = {
            "project": project,
            "content": content,
            "fact_type": fact_type,
        }
        if tags:
            body["tags"] = tags
        if source:
            body["source"] = source
        if meta:
            body["meta"] = meta

        resp = self._post("/v1/facts", body)
        return resp["fact_id"]

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        project: str | None = None,
        as_of: str | None = None,
        graph_depth: int = 0,
        include_graph: bool = False,
    ) -> list[Fact]:
        """
        Semantic search across stored facts.

        Args:
            query: Natural language query.
            top_k: Number of results (1-50).
            project: Filter by project.
            as_of: Time-travel query (ISO timestamp).
            graph_depth: Graph RAG expansion depth (0-5).
            include_graph: Include graph context in results.

        Returns:
            List of matching Facts sorted by relevance.
        """
        body: dict[str, Any] = {
            "query": query,
            "k": top_k,
        }
        if project:
            body["project"] = project
        if as_of:
            body["as_of"] = as_of
        if graph_depth:
            body["graph_depth"] = graph_depth
        if include_graph:
            body["include_graph"] = include_graph

        results = self._post("/v1/search", body)
        return [self._to_fact(r) for r in results]

    def recall(self, project: str, *, limit: int | None = None) -> list[Fact]:
        """
        Recall all facts for a project.

        Args:
            project: Project identifier.
            limit: Maximum number of facts to return (1-1000).

        Returns:
            List of Facts for the project.
        """
        params = f"?limit={limit}" if limit else ""
        results = self._get(f"/v1/projects/{project}/facts{params}")
        return [self._to_fact(r) for r in results]

    def deprecate(self, fact_id: int) -> bool:
        """
        Soft-deprecate a fact (mark as invalid).

        Returns:
            True if deprecation was successful.
        """
        resp = self._delete(f"/v1/facts/{fact_id}")
        return resp.get("success", False)

    # ── Ledger Operations ──────────────────────────────────────

    def verify(self) -> LedgerReport:
        """
        Verify cryptographic integrity of the entire ledger.

        Returns:
            LedgerReport with verification results.
        """
        resp = self._get("/v1/ledger/verify")
        return LedgerReport(
            valid=resp["valid"],
            violations=resp.get("violations", []),
            tx_checked=resp.get("tx_checked", 0),
            roots_checked=resp.get("roots_checked", 0),
            votes_checked=resp.get("votes_checked", 0),
        )

    def checkpoint(self) -> dict:
        """
        Create a Merkle root checkpoint.

        Returns:
            Checkpoint details including checkpoint_id.
        """
        return self._post("/v1/ledger/checkpoint", {})

    # ── Graph Operations ───────────────────────────────────────

    def graph(self, project: str | None = None, *, limit: int = 50) -> dict:
        """
        Get the entity knowledge graph.

        Args:
            project: Filter by project (None = all projects).
            limit: Maximum number of entities (1-500).

        Returns:
            Graph data with nodes and edges.
        """
        if project:
            return self._get(f"/v1/graph/{project}?limit={limit}")
        return self._get(f"/v1/graph?limit={limit}")

    # ── Voting ─────────────────────────────────────────────────

    def vote(self, fact_id: int, value: str = "verify") -> dict:
        """
        Cast a consensus vote on a fact.

        Args:
            fact_id: The fact to vote on.
            value: "verify" or "dispute".

        Returns:
            Vote result with updated consensus score.
        """
        return self._post(f"/v1/facts/{fact_id}/vote", {"value": value})

    # ── HTTP Primitives (zero dependencies) ────────────────────

    def _headers(self) -> dict[str, str]:
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _request(self, method: str, path: str, body: dict | None = None) -> Any:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body else None

        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(error_body).get("detail", error_body)
            except json.JSONDecodeError:
                detail = error_body
            raise CortexError(e.code, detail) from None

    def _get(self, path: str) -> Any:
        return self._request("GET", path)

    def _post(self, path: str, body: dict) -> Any:
        return self._request("POST", path, body)

    def _delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    @staticmethod
    def _to_fact(data: dict) -> Fact:
        return Fact(
            id=data.get("fact_id", data.get("id", 0)),
            project=data.get("project", ""),
            content=data.get("content", ""),
            fact_type=data.get("fact_type", "general"),
            tags=data.get("tags", []),
            confidence=data.get("confidence", "medium"),
            score=data.get("score"),
            created_at=data.get("created_at"),
            tx_id=data.get("tx_id"),
            hash=data.get("hash"),
            context=data.get("context"),
        )

    def __repr__(self) -> str:
        return f"Cortex(base_url={self.base_url!r})"

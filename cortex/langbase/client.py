# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v4.2 — Langbase HTTP Client.

Zero-dependency async client for the Langbase API.
Handles Pipes, Memory, and Tools endpoints.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger("cortex.langbase.client")

# Langbase API base
DEFAULT_BASE_URL = "https://api.langbase.com/v1"

# Timeouts
PIPE_TIMEOUT = 120.0  # Pipe runs can take time (LLM inference)
DEFAULT_TIMEOUT = 30.0


class LangbaseError(Exception):
    """Langbase API error."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Langbase API error {status_code}: {detail}")


class LangbaseClient:
    """Async HTTP client for the Langbase API.

    Usage::

        async with LangbaseClient(api_key="lb_...") as lb:
            result = await lb.run_pipe("my-pipe", [{"role": "user", "content": "Hello"}])
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        if not api_key:
            raise ValueError("LANGBASE_API_KEY is required")

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    async def __aenter__(self) -> LangbaseClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Shut down the HTTP client."""
        await self._client.aclose()

    # ─── Internal ────────────────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        timeout: float | None = None,
    ) -> dict:
        """Make an authenticated request to Langbase API."""
        try:
            resp = await self._client.request(
                method,
                path,
                json=json_body,
                timeout=timeout,
            )
        except httpx.TimeoutException as e:
            raise LangbaseError(408, f"Request timed out: {e}") from e
        except httpx.HTTPError as e:
            raise LangbaseError(0, f"HTTP error: {e}") from e

        if resp.status_code >= 400:
            try:
                detail = resp.json().get("error", {}).get("message", resp.text)
            except (ConnectionError, OSError):
                detail = resp.text
            raise LangbaseError(resp.status_code, detail)

        if resp.status_code == 204:
            return {"ok": True}

        return resp.json()

    # ─── Pipes (AI Agents) ───────────────────────────────────────────

    async def run_pipe(
        self,
        name: str,
        messages: list[dict[str, str]],
        *,
        thread_id: str | None = None,
        variables: list[dict[str, str]] | None = None,
    ) -> dict:
        """Run a Langbase Pipe (AI agent).

        Args:
            name: Pipe name (e.g. "my-pipe")
            messages: Chat messages [{"role": "user", "content": "..."}]
            thread_id: Optional thread ID for conversation context
            variables: Optional variables to inject into the pipe

        Returns:
            Pipe completion response with 'completion' key
        """
        body: dict[str, Any] = {"messages": messages}
        if thread_id:
            body["threadId"] = thread_id
        if variables:
            body["variables"] = variables

        return await self._request(
            "POST",
            "/pipes/run",
            json_body=body,
            timeout=PIPE_TIMEOUT,
        )

    async def list_pipes(self) -> list[dict]:
        """List all Pipes in the account."""
        result = await self._request("GET", "/pipes")
        return result if isinstance(result, list) else result.get("data", [])

    async def create_pipe(
        self,
        name: str,
        *,
        description: str = "",
        model: str = "openai:gpt-4o-mini",
        system_prompt: str = "",
        memory: list[dict] | None = None,
    ) -> dict:
        """Create a new Pipe (AI agent).

        Args:
            name: Unique pipe name
            description: Human-readable description
            model: LLM model identifier (e.g. "openai:gpt-4o-mini")
            system_prompt: System prompt for the agent
            memory: Optional list of memory refs to attach
        """
        body: dict[str, Any] = {
            "name": name,
            "description": description,
            "model": model,
        }
        if system_prompt:
            body["systemPrompt"] = system_prompt
        if memory:
            body["memory"] = memory

        return await self._request("POST", "/pipes", json_body=body)

    # ─── Memory (RAG) ────────────────────────────────────────────────

    async def list_memories(self) -> list[dict]:
        """List all Memory sets."""
        result = await self._request("GET", "/memory")
        return result if isinstance(result, list) else result.get("data", [])

    async def create_memory(
        self,
        name: str,
        *,
        description: str = "",
    ) -> dict:
        """Create a new Memory set for RAG.

        Args:
            name: Unique memory name
            description: Human-readable description
        """
        return await self._request(
            "POST",
            "/memory",
            json_body={"name": name, "description": description},
        )

    async def delete_memory(self, name: str) -> dict:
        """Delete a Memory set."""
        return await self._request("DELETE", f"/memory/{name}")

    async def retrieve_memory(
        self,
        name: str,
        query: str,
        *,
        top_k: int = 5,
    ) -> list[dict]:
        """Semantic search in a Memory set.

        Args:
            name: Memory name
            query: Natural language query
            top_k: Number of results to return

        Returns:
            List of matching chunks with score and content
        """
        result = await self._request(
            "POST",
            f"/memory/{name}/retrieve",
            json_body={"query": query, "topK": top_k},
        )
        return result if isinstance(result, list) else result.get("data", [])

    async def upload_document(
        self,
        memory_name: str,
        content: str,
        filename: str,
        *,
        meta: dict | None = None,
    ) -> dict:
        """Upload a document to a Memory set.

        Args:
            memory_name: Target memory name
            content: Document text content
            filename: Document filename (e.g. "fact-42.md")
            meta: Optional metadata dict

        Returns:
            Upload confirmation with document ID
        """
        # Langbase expects multipart or base64 — we use the text content approach
        body: dict[str, Any] = {
            "fileName": filename,
            "content": content,
        }
        if meta:
            body["meta"] = meta

        return await self._request(
            "POST",
            f"/memory/{memory_name}/documents",
            json_body=body,
        )

    async def list_documents(self, memory_name: str) -> list[dict]:
        """List all documents in a Memory set."""
        result = await self._request("GET", f"/memory/{memory_name}/documents")
        return result if isinstance(result, list) else result.get("data", [])

    # ─── Tools ───────────────────────────────────────────────────────

    async def web_search(self, query: str) -> list[dict]:
        """Search the web via Langbase Tools API.

        Args:
            query: Search query

        Returns:
            List of web results
        """
        result = await self._request(
            "POST",
            "/tools/web-search",
            json_body={"query": query},
        )
        return result if isinstance(result, list) else result.get("data", [])

    async def crawl_url(self, url: str) -> dict:
        """Crawl a URL via Langbase Tools API.

        Args:
            url: URL to crawl

        Returns:
            Crawled content (markdown)
        """
        return await self._request(
            "POST",
            "/tools/crawl",
            json_body={"url": url},
            timeout=60.0,
        )

    # ─── Status ──────────────────────────────────────────────────────

    async def status(self) -> dict:
        """Check Langbase API connectivity.

        Returns:
            Dict with 'connected' bool and resource counts
        """
        try:
            pipes = await self.list_pipes()
            memories = await self.list_memories()
            return {
                "connected": True,
                "pipes_count": len(pipes),
                "memories_count": len(memories),
            }
        except LangbaseError as e:
            return {
                "connected": False,
                "error": e.detail,
                "status_code": e.status_code,
            }
        except (ConnectionError, OSError, RuntimeError) as e:
            return {
                "connected": False,
                "error": str(e),
            }

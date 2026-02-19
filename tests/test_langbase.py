# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v4.2 — Langbase Integration Tests.

All tests use mocked HTTP responses — no real API key needed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from cortex.langbase.client import LangbaseClient, LangbaseError
from cortex.langbase.sync import _fact_to_markdown, sync_to_langbase, enrich_from_langbase
from cortex.langbase.pipe import _format_facts, run_with_cortex_context

# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def mock_transport():
    """Create a mock httpx transport that returns predefined responses."""

    class MockTransport(httpx.AsyncBaseTransport):
        def __init__(self):
            self.requests: list[httpx.Request] = []
            self.responses: dict[str, httpx.Response] = {}

        def add_response(self, method: str, path: str, json_data: dict, status_code: int = 200):
            key = f"{method.upper()} {path}"
            self.responses[key] = httpx.Response(
                status_code=status_code,
                json=json_data,
                request=httpx.Request(method, path),
            )

        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            key = f"{request.method} {request.url.raw_path.decode()}"
            if key in self.responses:
                return self.responses[key]
            # Default: return 200 with empty JSON
            return httpx.Response(
                200,
                json={"ok": True},
                request=request,
            )

    return MockTransport()


@pytest.fixture
def client(mock_transport):
    """Create a LangbaseClient with a mock transport."""
    c = LangbaseClient(api_key="lb_test_key_123", base_url="https://api.langbase.com/v1")
    # Replace the internal httpx client with our mocked one
    c._client = httpx.AsyncClient(
        transport=mock_transport,
        base_url="https://api.langbase.com/v1",
        headers={"Authorization": "Bearer lb_test_key_123", "Content-Type": "application/json"},
    )
    c._mock_transport = mock_transport  # Expose for test assertions
    return c


@dataclass
class FakeFact:
    """Fake fact object that mimics CORTEX Fact dataclass."""

    id: int
    project: str
    content: str
    fact_type: str = "knowledge"
    confidence: str = "verified"
    tags: list[str] | None = None
    created_at: str = "2026-02-19T10:00:00Z"


@dataclass
class FakeSearchResult:
    """Fake search result from CORTEX engine."""

    fact_id: int
    project: str
    content: str
    fact_type: str = "knowledge"
    score: float = 0.85


# ─── Client Tests ────────────────────────────────────────────────────


class TestLangbaseClient:
    """Test the LangbaseClient HTTP wrapper."""

    def test_init_requires_api_key(self):
        """Client creation fails without API key."""
        with pytest.raises(ValueError, match="LANGBASE_API_KEY"):
            LangbaseClient(api_key="")

    def test_init_with_key(self):
        """Client creation succeeds with API key."""
        c = LangbaseClient(api_key="lb_test_123")
        assert c._api_key == "lb_test_123"

    @pytest.mark.asyncio
    async def test_run_pipe(self, client, mock_transport):
        """Test running a Pipe with messages."""
        mock_transport.add_response(
            "POST",
            "/v1/pipes/run",
            {"completion": "Hello from Langbase!", "threadId": "t-123"},
        )

        result = await client.run_pipe(
            name="test-pipe",
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert result["completion"] == "Hello from Langbase!"
        assert result["threadId"] == "t-123"
        assert len(mock_transport.requests) == 1

    @pytest.mark.asyncio
    async def test_run_pipe_with_thread(self, client, mock_transport):
        """Test running a Pipe with thread context."""
        mock_transport.add_response(
            "POST",
            "/v1/pipes/run",
            {"completion": "Continued conversation"},
        )

        result = await client.run_pipe(
            name="test-pipe",
            messages=[{"role": "user", "content": "Continue"}],
            thread_id="t-456",
        )

        assert result["completion"] == "Continued conversation"
        # Verify threadId was sent in the request body
        req = mock_transport.requests[0]
        body = json.loads(req.content)
        assert body["threadId"] == "t-456"

    @pytest.mark.asyncio
    async def test_list_pipes(self, client, mock_transport):
        """Test listing Pipes."""
        mock_transport.add_response(
            "GET",
            "/v1/pipes",
            {"data": [{"name": "pipe-1"}, {"name": "pipe-2"}]},
        )

        result = await client.list_pipes()
        assert len(result) == 2
        assert result[0]["name"] == "pipe-1"

    @pytest.mark.asyncio
    async def test_create_memory(self, client, mock_transport):
        """Test creating a Memory set."""
        mock_transport.add_response(
            "POST",
            "/v1/memory",
            {"name": "cortex-test", "status": "created"},
        )

        result = await client.create_memory("cortex-test", description="Test memory")
        assert result["name"] == "cortex-test"

    @pytest.mark.asyncio
    async def test_retrieve_memory(self, client, mock_transport):
        """Test semantic search in Memory."""
        mock_transport.add_response(
            "POST",
            "/v1/memory/cortex-test/retrieve",
            {
                "data": [
                    {"content": "Decision about architecture", "score": 0.95},
                    {"content": "Error in auth module", "score": 0.72},
                ]
            },
        )

        results = await client.retrieve_memory("cortex-test", "architecture decisions")
        assert len(results) == 2
        assert results[0]["score"] == 0.95

    @pytest.mark.asyncio
    async def test_upload_document(self, client, mock_transport):
        """Test uploading a document to Memory."""
        mock_transport.add_response(
            "POST",
            "/v1/memory/cortex-test/documents",
            {"documentId": "doc-123", "status": "uploaded"},
        )

        result = await client.upload_document(
            memory_name="cortex-test",
            content="# Fact content\nSome important decision",
            filename="fact-42.md",
        )
        assert result["documentId"] == "doc-123"

    @pytest.mark.asyncio
    async def test_web_search(self, client, mock_transport):
        """Test web search via Tools API."""
        mock_transport.add_response(
            "POST",
            "/v1/tools/web-search",
            {"data": [{"title": "Result 1", "url": "https://example.com"}]},
        )

        results = await client.web_search("CORTEX AI memory")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_status_connected(self, client, mock_transport):
        """Test status check when connected."""
        mock_transport.add_response("GET", "/v1/pipes", {"data": [{"name": "p1"}]})
        mock_transport.add_response("GET", "/v1/memory", {"data": [{"name": "m1"}, {"name": "m2"}]})

        status = await client.status()
        assert status["connected"] is True
        assert status["pipes_count"] == 1
        assert status["memories_count"] == 2

    @pytest.mark.asyncio
    async def test_close(self, client):
        """Test client cleanup."""
        await client.close()
        # Verify the client is closed (subsequent calls would fail)
        assert client._client.is_closed


# ─── Sync Tests ──────────────────────────────────────────────────────


class TestSync:
    """Test CORTEX ↔ Langbase synchronization."""

    def test_fact_to_markdown(self):
        """Test fact → markdown conversion."""
        fact = {
            "id": 42,
            "project": "cortex",
            "content": "Implemented vector search with ONNX embeddings",
            "fact_type": "decision",
            "confidence": "verified",
            "tags": ["architecture", "search"],
            "created_at": "2026-02-19T10:00:00Z",
        }

        md = _fact_to_markdown(fact)
        assert "fact_id: 42" in md
        assert "project: cortex" in md
        assert "type: decision" in md
        assert "confidence: verified" in md
        assert "tags: architecture, search" in md
        assert "Implemented vector search" in md
        assert md.startswith("---")

    def test_fact_to_markdown_minimal(self):
        """Test markdown conversion with minimal fact data."""
        fact = {"id": 1, "content": "Simple fact"}
        md = _fact_to_markdown(fact)
        assert "fact_id: 1" in md
        assert "Simple fact" in md

    @pytest.mark.asyncio
    async def test_sync_to_langbase(self):
        """Test syncing CORTEX facts to Langbase Memory."""
        # Mock engine
        engine = AsyncMock()
        engine.recall = AsyncMock(return_value=[
            FakeFact(id=1, project="cortex", content="First decision"),
            FakeFact(id=2, project="cortex", content="Second decision"),
        ])

        # Mock client
        client = AsyncMock()
        client.create_memory = AsyncMock(return_value={"name": "cortex-cortex"})
        client.upload_document = AsyncMock(return_value={"documentId": "doc-1"})

        result = await sync_to_langbase(
            client=client,
            engine=engine,
            project="cortex",
        )

        assert result["synced"] == 2
        assert result["errors"] == 0
        assert result["memory"] == "cortex-cortex"
        assert client.upload_document.call_count == 2

    @pytest.mark.asyncio
    async def test_sync_empty_project(self):
        """Test syncing a project with no facts."""
        engine = AsyncMock()
        engine.recall = AsyncMock(return_value=[])

        client = AsyncMock()

        result = await sync_to_langbase(
            client=client,
            engine=engine,
            project="empty-project",
        )

        assert result["synced"] == 0
        assert "No facts to sync" in result["message"]

    @pytest.mark.asyncio
    async def test_enrich_from_langbase(self):
        """Test enriching CORTEX from Langbase Memory search."""
        engine = AsyncMock()
        engine.store = AsyncMock(return_value=1)

        client = AsyncMock()
        client.retrieve_memory = AsyncMock(return_value=[
            {"content": "External knowledge chunk 1", "score": 0.9},
            {"content": "External knowledge chunk 2", "score": 0.7},
        ])

        result = await enrich_from_langbase(
            client=client,
            engine=engine,
            memory_name="external-docs",
            query="architecture patterns",
        )

        assert result["stored"] == 2
        assert result["source_memory"] == "external-docs"
        assert engine.store.call_count == 2


# ─── Pipe Tests ──────────────────────────────────────────────────────


class TestPipe:
    """Test Pipe execution with CORTEX context."""

    def test_format_facts_empty(self):
        """Test formatting with no facts."""
        result = _format_facts([])
        assert "No relevant facts" in result

    def test_format_facts(self):
        """Test formatting search results into context."""
        facts = [
            FakeSearchResult(fact_id=1, project="cortex", content="Decision A", score=0.95),
            FakeSearchResult(fact_id=2, project="cortex", content="Decision B", score=0.80),
        ]

        result = _format_facts(facts)
        assert "[Fact #1]" in result
        assert "[Fact #2]" in result
        assert "Decision A" in result
        assert "0.950" in result  # Score formatted

    @pytest.mark.asyncio
    async def test_run_with_cortex_context(self):
        """Test running a Pipe with CORTEX memory injection."""
        # Mock CORTEX engine
        engine = AsyncMock()
        engine.search = AsyncMock(return_value=[
            FakeSearchResult(fact_id=42, project="cortex", content="CORTEX uses vector search"),
        ])

        # Mock Langbase client
        client = AsyncMock()
        client.run_pipe = AsyncMock(return_value={
            "completion": "Based on the facts, CORTEX uses vector search for semantic retrieval.",
            "threadId": "t-789",
        })

        result = await run_with_cortex_context(
            client=client,
            engine=engine,
            pipe_name="analyst-pipe",
            query="What search technology does CORTEX use?",
            project="cortex",
        )

        assert "completion" in result
        assert result["facts_used"] == 1
        assert result["pipe_name"] == "analyst-pipe"
        assert len(result["sources"]) == 1
        assert result["sources"][0]["fact_id"] == 42

        # Verify the pipe received enriched content
        pipe_call = client.run_pipe.call_args
        messages = pipe_call.kwargs.get("messages") or pipe_call.args[1]
        assert "CORTEX Memory Context" in messages[0]["content"]
        assert "[Fact #42]" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_run_with_no_facts(self):
        """Test Pipe execution when CORTEX has no matching facts."""
        engine = AsyncMock()
        engine.search = AsyncMock(return_value=[])

        client = AsyncMock()
        client.run_pipe = AsyncMock(return_value={"completion": "No context available."})

        result = await run_with_cortex_context(
            client=client,
            engine=engine,
            pipe_name="test-pipe",
            query="Unknown topic",
        )

        assert result["facts_used"] == 0
        assert result["sources"] == []


# ─── Error Handling Tests ────────────────────────────────────────────


class TestErrorHandling:
    """Test error cases and graceful degradation."""

    @pytest.mark.asyncio
    async def test_langbase_error(self, client, mock_transport):
        """Test handling of Langbase API errors."""
        mock_transport.add_response(
            "GET",
            "/v1/pipes",
            {"error": {"message": "Invalid API key"}},
            status_code=401,
        )

        with pytest.raises(LangbaseError) as exc_info:
            await client.list_pipes()

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_sync_with_upload_errors(self):
        """Test sync continues despite individual upload failures."""
        engine = AsyncMock()
        engine.recall = AsyncMock(return_value=[
            FakeFact(id=1, project="test", content="Good fact"),
            FakeFact(id=2, project="test", content="Bad fact"),
            FakeFact(id=3, project="test", content="Good fact 2"),
        ])

        client = AsyncMock()
        client.create_memory = AsyncMock(return_value={"name": "cortex-test"})

        # Second upload fails
        client.upload_document = AsyncMock(
            side_effect=[
                {"documentId": "d1"},
                LangbaseError(500, "Upload failed"),
                {"documentId": "d3"},
            ]
        )

        result = await sync_to_langbase(
            client=client,
            engine=engine,
            project="test",
        )

        assert result["synced"] == 2
        assert result["errors"] == 1
        assert result["total"] == 3

    @pytest.mark.asyncio
    async def test_status_disconnected(self, client, mock_transport):
        """Test status when Langbase is unreachable."""
        mock_transport.add_response(
            "GET",
            "/v1/pipes",
            {"error": {"message": "Service unavailable"}},
            status_code=503,
        )

        status = await client.status()
        assert status["connected"] is False
        assert "error" in status

"""
Integration tests for CORTEX × Open-Antigravity.

These tests verify that the CORTEX Memory Engine is properly accessible
and functional within the Open-Antigravity Docker stack.

Run with:
    pytest tests/test_integration.py -v

Prerequisites:
    docker-compose -f docker-compose.yml -f docker-compose.cortex.yml up -d
"""

from __future__ import annotations

import os
import sys
import pytest

# Add parent dir so cortex_client is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cortex_client import CortexMemoryClient


CORTEX_URL = os.getenv("CORTEX_URL", "http://localhost:8484")
INTEGRATION = os.getenv("INTEGRATION_TESTS", "0") == "1"

skip_unless_integration = pytest.mark.skipif(
    not INTEGRATION,
    reason="Set INTEGRATION_TESTS=1 to run (requires running Docker stack)",
)


# ─── Unit Tests (no Docker needed) ──────────────────────────────────


class TestClientConstruction:
    """Test client construction without network calls."""

    def test_default_url(self):
        client = CortexMemoryClient()
        assert "localhost" in client.base_url or "cortex" in client.base_url

    def test_custom_url(self):
        client = CortexMemoryClient(base_url="http://my-cortex:9999")
        assert client.base_url == "http://my-cortex:9999"

    def test_api_key_header(self):
        client = CortexMemoryClient(api_key="test-key-123")
        assert client._headers["Authorization"] == "Bearer test-key-123"

    def test_no_api_key(self):
        client = CortexMemoryClient(api_key="")
        assert "Authorization" not in client._headers

    def test_trailing_slash_stripped(self):
        client = CortexMemoryClient(base_url="http://localhost:8484/")
        assert client.base_url == "http://localhost:8484"


# ─── Integration Tests (require Docker stack) ───────────────────────


@skip_unless_integration
class TestHealthIntegration:
    """Test CORTEX health within the Docker stack."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        async with CortexMemoryClient(base_url=CORTEX_URL) as client:
            data = await client.health()
            assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_is_alive(self):
        async with CortexMemoryClient(base_url=CORTEX_URL) as client:
            assert await client.is_alive() is True

    @pytest.mark.asyncio
    async def test_status(self):
        async with CortexMemoryClient(base_url=CORTEX_URL) as client:
            data = await client.status()
            assert "version" in data or "total_facts" in data


@skip_unless_integration
class TestMemoryIntegration:
    """Test store/recall/search cycle."""

    PROJECT = "open-antigravity-test"

    @pytest.mark.asyncio
    async def test_store_and_recall(self):
        async with CortexMemoryClient(base_url=CORTEX_URL) as client:
            # Store a decision
            result = await client.store_decision(
                self.PROJECT,
                "Integration test: chose CORTEX as memory engine",
                tags=["integration", "test"],
            )
            assert "id" in result

            # Recall
            facts = await client.recall(self.PROJECT, limit=10)
            assert len(facts) > 0
            contents = [f.get("content", "") for f in facts]
            assert any("CORTEX" in c for c in contents)

    @pytest.mark.asyncio
    async def test_semantic_search(self):
        async with CortexMemoryClient(base_url=CORTEX_URL) as client:
            # Store something searchable
            await client.store_fact(
                self.PROJECT,
                "The authentication system uses JWT tokens with RS256 signing",
                tags=["architecture", "auth"],
            )

            # Search for it semantically
            results = await client.search("how does auth work?", k=5)
            assert len(results) > 0

    @pytest.mark.asyncio
    async def test_agent_lifecycle(self):
        """Simulate a full agent lifecycle: start → work → complete."""
        async with CortexMemoryClient(base_url=CORTEX_URL) as client:
            agent_id = "test-agent-001"

            # Agent starts — gets context
            context = await client.on_agent_start(
                agent_id, self.PROJECT, "Implement login page"
            )
            assert isinstance(context, list)

            # Agent completes — persists decisions
            await client.on_agent_complete(
                agent_id,
                self.PROJECT,
                "Implemented login page with OAuth",
                decisions=[
                    "Used OAuth2 PKCE flow for security",
                    "Chose Google as default provider",
                ],
            )

            # Verify decisions were stored
            facts = await client.recall(self.PROJECT, limit=20)
            contents = [f.get("content", "") for f in facts]
            assert any("OAuth2 PKCE" in c for c in contents)

    @pytest.mark.asyncio
    async def test_error_persistence(self):
        """Verify agent errors are persisted for learning."""
        async with CortexMemoryClient(base_url=CORTEX_URL) as client:
            await client.on_agent_error(
                "test-agent-002",
                self.PROJECT,
                "TypeError: Cannot read property 'map' of undefined",
            )

            # Search for the error
            results = await client.search("TypeError map undefined", k=3)
            assert len(results) > 0

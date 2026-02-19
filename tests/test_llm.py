# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v4.2 — LLM Provider Tests.

Tests for:
- LLMProvider instantiation with all presets
- Custom provider mode
- LLMManager graceful degradation
- /v1/ask endpoint (503 when no LLM)
- /v1/llm/status endpoint
"""

import tempfile
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import cortex.api
import cortex.config

# Set test DB path
_test_db = tempfile.mktemp(suffix=".db")
cortex.config.DB_PATH = _test_db
cortex.api.DB_PATH = _test_db

from cortex.api import app


# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    """Test client with bootstrapped DB."""
    from cortex.engine import CortexEngine

    CortexEngine(db_path=_test_db).init_db_sync()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def api_key(client):
    """Bootstrap API key."""
    resp = client.post("/v1/admin/keys?name=test-llm&tenant_id=test")
    assert resp.status_code == 200
    return resp.json()["key"]


@pytest.fixture(scope="module")
def auth_headers(api_key):
    return {"Authorization": f"Bearer {api_key}"}


# ─── LLMProvider Unit Tests ──────────────────────────────────────────


class TestLLMProvider:
    def test_list_providers(self):
        from cortex.llm.provider import LLMProvider

        providers = LLMProvider.list_providers()
        assert "qwen" in providers
        assert "openai" in providers
        assert "ollama" in providers
        assert "openrouter" in providers
        assert "groq" in providers
        assert "together" in providers
        assert "deepseek" in providers
        assert "anthropic" in providers
        assert "gemini" in providers
        assert "mistral" in providers
        assert "cerebras" in providers
        assert "fireworks" in providers
        assert "deepinfra" in providers
        assert "perplexity" in providers
        assert "xai" in providers
        assert "cohere" in providers
        assert "sambanova" in providers
        assert "lmstudio" in providers
        assert "llamacpp" in providers
        assert "vllm" in providers
        assert "jan" in providers
        assert "custom" in providers
        assert len(providers) >= 25  # 24 presets + custom

    def test_get_preset_info(self):
        from cortex.llm.provider import LLMProvider

        info = LLMProvider.get_preset_info("qwen")
        assert info is not None
        assert "base_url" in info
        assert "default_model" in info
        assert info["context_window"] == 131072

    def test_get_preset_info_unknown(self):
        from cortex.llm.provider import LLMProvider

        assert LLMProvider.get_preset_info("nonexistent") is None

    def test_unknown_provider_raises(self):
        from cortex.llm.provider import LLMProvider

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            LLMProvider(provider="nonexistent_provider")

    def test_missing_api_key_raises(self):
        from cortex.llm.provider import LLMProvider

        with pytest.raises(ValueError, match="required"):
            LLMProvider(provider="qwen", api_key="")

    def test_local_providers_no_key_needed(self):
        """Ollama, LM Studio, llama.cpp, vLLM, Jan don't need API keys."""
        from cortex.llm.provider import LLMProvider

        for name in ["ollama", "lmstudio", "llamacpp", "vllm", "jan"]:
            provider = LLMProvider(provider=name)
            assert provider.provider_name == name
            assert provider.context_window == 32768

    def test_custom_provider_requires_base_url(self):
        from cortex.llm.provider import LLMProvider

        with pytest.raises(ValueError, match="CORTEX_LLM_BASE_URL"):
            LLMProvider(provider="custom")

    def test_custom_provider_with_url(self):
        from cortex.llm.provider import LLMProvider

        p = LLMProvider(
            provider="custom",
            base_url="http://my-server:8080/v1",
            model="my-model",
        )
        assert p.provider_name == "custom"
        assert p.model == "my-model"

    def test_preset_with_explicit_key(self):
        from cortex.llm.provider import LLMProvider

        p = LLMProvider(provider="qwen", api_key="test-key-123")
        assert p.provider_name == "qwen"
        assert p.model == "qwen-plus"

    def test_repr(self):
        from cortex.llm.provider import LLMProvider

        p = LLMProvider(provider="ollama")
        assert "ollama" in repr(p)
        assert "qwen2.5" in repr(p)


# ─── LLMManager Tests ───────────────────────────────────────────────


class TestLLMManager:
    def test_no_provider_configured(self):
        from cortex.llm.manager import LLMManager

        with patch.dict("os.environ", {"CORTEX_LLM_PROVIDER": ""}, clear=False):
            mgr = LLMManager()
            assert not mgr.available
            assert mgr.provider is None

    def test_provider_configured_ollama(self):
        from cortex.llm.manager import LLMManager

        with patch.dict("os.environ", {"CORTEX_LLM_PROVIDER": "ollama"}, clear=False):
            mgr = LLMManager()
            assert mgr.available
            assert mgr.provider is not None
            assert mgr.provider_name == "ollama"

    def test_invalid_provider_graceful(self):
        """Invalid provider name should not crash, just log error."""
        from cortex.llm.manager import LLMManager

        with patch.dict("os.environ", {"CORTEX_LLM_PROVIDER": "nonexistent"}, clear=False):
            mgr = LLMManager()
            assert not mgr.available
            assert mgr.provider is None

    @pytest.mark.asyncio
    async def test_complete_without_provider(self):
        from cortex.llm.manager import LLMManager

        with patch.dict("os.environ", {"CORTEX_LLM_PROVIDER": ""}, clear=False):
            mgr = LLMManager()
            result = await mgr.complete("test prompt")
            assert result is None


# ─── API Endpoint Tests ─────────────────────────────────────────────


class TestAskEndpoint:
    def test_ask_returns_503_without_llm(self, client, auth_headers):
        """When no LLM is configured, /v1/ask returns 503."""
        resp = client.post(
            "/v1/ask",
            json={"query": "What database does CORTEX use?"},
            headers=auth_headers,
        )
        # Should be 503 (no LLM configured in test env)
        assert resp.status_code == 503
        data = resp.json()
        assert "No LLM provider configured" in data["detail"]
        assert "Supported" in data["detail"]

    def test_ask_requires_auth(self, client):
        """Ask endpoint requires authentication."""
        resp = client.post(
            "/v1/ask",
            json={"query": "test"},
        )
        assert resp.status_code == 401

    def test_ask_validates_empty_query(self, client, auth_headers):
        """Empty query should fail validation."""
        resp = client.post(
            "/v1/ask",
            json={"query": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestLLMStatusEndpoint:
    def test_llm_status(self, client, auth_headers):
        """GET /v1/llm/status returns provider info."""
        resp = client.get("/v1/llm/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "available" in data
        assert "supported_providers" in data
        providers = data["supported_providers"]
        assert "qwen" in providers
        assert "custom" in providers
        assert len(providers) >= 25

    def test_llm_status_requires_auth(self, client):
        resp = client.get("/v1/llm/status")
        assert resp.status_code == 401

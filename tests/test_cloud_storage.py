"""
Tests for CORTEX Cloud Storage Layer.

Tests the storage abstraction, Turso backend, and tenant router
without requiring actual Turso credentials (uses mocking).
"""

from __future__ import annotations

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─── Storage __init__ Tests ──────────────────────────────────────────


class TestStorageMode:
    """Test storage mode detection from environment."""

    def test_default_is_local(self):
        """Default mode should be local when no env var set."""
        from cortex.storage import StorageMode, get_storage_mode

        with patch.dict(os.environ, {}, clear=True):
            # Remove CORTEX_STORAGE if present
            os.environ.pop("CORTEX_STORAGE", None)
            mode = get_storage_mode()
            assert mode == StorageMode.LOCAL

    def test_turso_mode(self):
        from cortex.storage import StorageMode, get_storage_mode

        with patch.dict(os.environ, {"CORTEX_STORAGE": "turso"}):
            mode = get_storage_mode()
            assert mode == StorageMode.TURSO

    def test_invalid_mode_falls_back(self):
        from cortex.storage import StorageMode, get_storage_mode

        with patch.dict(os.environ, {"CORTEX_STORAGE": "oracle"}):
            mode = get_storage_mode()
            assert mode == StorageMode.LOCAL

    def test_get_storage_config_local(self):
        from cortex.storage import get_storage_config, StorageMode

        with patch.dict(os.environ, {"CORTEX_STORAGE": "local"}):
            config = get_storage_config()
            assert config["mode"] == StorageMode.LOCAL
            assert "url" not in config

    def test_get_storage_config_turso_requires_url(self):
        from cortex.storage import get_storage_config

        with patch.dict(os.environ, {"CORTEX_STORAGE": "turso"}, clear=True):
            os.environ.pop("TURSO_DATABASE_URL", None)
            os.environ.pop("TURSO_AUTH_TOKEN", None)
            with pytest.raises(ValueError, match="TURSO_DATABASE_URL"):
                get_storage_config()

    def test_get_storage_config_turso_requires_token(self):
        from cortex.storage import get_storage_config

        with patch.dict(
            os.environ,
            {"CORTEX_STORAGE": "turso", "TURSO_DATABASE_URL": "libsql://test.turso.io"},
            clear=True,
        ):
            os.environ.pop("TURSO_AUTH_TOKEN", None)
            with pytest.raises(ValueError, match="TURSO_AUTH_TOKEN"):
                get_storage_config()

    def test_get_storage_config_turso_complete(self):
        from cortex.storage import get_storage_config, StorageMode

        with patch.dict(
            os.environ,
            {
                "CORTEX_STORAGE": "turso",
                "TURSO_DATABASE_URL": "libsql://cortex.turso.io",
                "TURSO_AUTH_TOKEN": "test-token-123",
            },
        ):
            config = get_storage_config()
            assert config["mode"] == StorageMode.TURSO
            assert config["url"] == "libsql://cortex.turso.io"
            assert config["token"] == "test-token-123"


# ─── TursoBackend Tests ──────────────────────────────────────────────


class TestTursoBackend:
    """Test Turso backend without actual Turso connection."""

    def test_tenant_db_url(self):
        from cortex.storage.turso import TursoBackend

        url = TursoBackend.tenant_db_url("libsql://cortex.turso.io", "alice")
        assert url == "libsql://cortex-alice.turso.io"

    def test_tenant_db_url_complex(self):
        from cortex.storage.turso import TursoBackend

        url = TursoBackend.tenant_db_url("libsql://myapp-prod.turso.io", "bob")
        assert url == "libsql://myapp-prod-bob.turso.io"

    def test_repr(self):
        from cortex.storage.turso import TursoBackend

        # Can't import libsql_experimental, so we test repr directly
        backend = TursoBackend.__new__(TursoBackend)
        backend.url = "libsql://test.turso.io"
        backend._conn = None
        assert "test.turso.io" in repr(backend)
        assert "connected=False" in repr(backend)

    def test_ensure_conn_raises_when_not_connected(self):
        from cortex.storage.turso import TursoBackend

        backend = TursoBackend.__new__(TursoBackend)
        backend._conn = None
        with pytest.raises(RuntimeError, match="not connected"):
            backend._ensure_conn()


# ─── TenantRouter Tests ──────────────────────────────────────────────


class TestTenantRouter:
    """Test tenant routing logic."""

    def test_router_detects_local_mode(self):
        with patch.dict(os.environ, {"CORTEX_STORAGE": "local"}):
            from cortex.storage.router import TenantRouter
            from cortex.storage import StorageMode

            router = TenantRouter()
            assert router.mode == StorageMode.LOCAL

    def test_router_repr(self):
        with patch.dict(os.environ, {"CORTEX_STORAGE": "local"}):
            from cortex.storage.router import TenantRouter

            router = TenantRouter()
            assert "local" in repr(router)
            assert "active_tenants=0" in repr(router)

    def test_router_active_tenants_empty(self):
        with patch.dict(os.environ, {"CORTEX_STORAGE": "local"}):
            from cortex.storage.router import TenantRouter

            router = TenantRouter()
            assert router.active_tenants == []


# ─── EmbeddingManager Mode Tests ─────────────────────────────────────


class TestEmbeddingManagerModes:
    """Test that EmbeddingManager selects the right provider."""

    def test_default_mode_is_local(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CORTEX_EMBEDDINGS", None)
            from cortex.embeddings.manager import EmbeddingManager

            mgr = EmbeddingManager()
            assert mgr.mode == "local"
            assert not mgr.is_cloud

    def test_api_mode(self):
        with patch.dict(os.environ, {"CORTEX_EMBEDDINGS": "api"}):
            from cortex.embeddings.manager import EmbeddingManager

            mgr = EmbeddingManager()
            assert mgr.mode == "api"
            assert mgr.is_cloud

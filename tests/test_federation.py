"""Tests for CORTEX v4.1 — Tenant Sharding (Federation).

Tests shard isolation, cross-shard search, tenant ID sanitization, and factory.
"""

import pytest
from unittest.mock import patch

from cortex.federation import FederatedEngine, get_engine


class TestFederatedEngine:
    """Tests for the FederatedEngine."""

    @pytest.mark.asyncio
    async def test_shard_creation(self, tmp_path):
        """Each tenant should get its own .db file."""
        engine = FederatedEngine(shard_dir=tmp_path, auto_embed=False)

        shard_a = await engine.get_shard("tenant-a")
        shard_b = await engine.get_shard("tenant-b")

        assert shard_a is not shard_b
        assert (tmp_path / "tenant-a.db").exists()
        assert (tmp_path / "tenant-b.db").exists()
        assert engine.shard_count == 2

        await engine.close_all()

    @pytest.mark.asyncio
    async def test_shard_reuse(self, tmp_path):
        """Same tenant ID should return the same engine instance."""
        engine = FederatedEngine(shard_dir=tmp_path, auto_embed=False)

        shard1 = await engine.get_shard("tenant-x")
        shard2 = await engine.get_shard("tenant-x")

        assert shard1 is shard2
        assert engine.shard_count == 1

        await engine.close_all()

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, tmp_path):
        """Facts stored in one tenant should not leak to another."""
        engine = FederatedEngine(shard_dir=tmp_path, auto_embed=False)

        await engine.store("tenant-a", "project-a", "Secret fact A")
        await engine.store("tenant-b", "project-b", "Secret fact B")

        facts_a = await engine.recall("tenant-a", "project-a")
        facts_b = await engine.recall("tenant-b", "project-b")

        # Each should only see its own facts
        contents_a = [f["content"] if isinstance(f, dict) else f.content for f in facts_a]
        contents_b = [f["content"] if isinstance(f, dict) else f.content for f in facts_b]

        assert "Secret fact A" in str(contents_a)
        assert "Secret fact B" not in str(contents_a)
        assert "Secret fact B" in str(contents_b)

        await engine.close_all()

    @pytest.mark.asyncio
    async def test_tenants_list(self, tmp_path):
        """tenants property should list all active tenants."""
        engine = FederatedEngine(shard_dir=tmp_path, auto_embed=False)

        await engine.get_shard("alpha")
        await engine.get_shard("beta")
        await engine.get_shard("gamma")

        assert set(engine.tenants) == {"alpha", "beta", "gamma"}
        await engine.close_all()


class TestTenantIdSanitization:
    """Tests for tenant ID sanitization."""

    def test_valid_ids(self):
        """Normal IDs should pass through."""
        assert FederatedEngine._sanitize_tenant_id("my-tenant") == "my-tenant"
        assert FederatedEngine._sanitize_tenant_id("tenant_123") == "tenant_123"

    def test_special_chars_replaced(self):
        """Special characters should be replaced with underscores."""
        assert FederatedEngine._sanitize_tenant_id("tenant@evil.com") == "tenant_evil_com"
        assert FederatedEngine._sanitize_tenant_id("../../../etc/passwd") == "_________etc_passwd"

    def test_empty_id_rejected(self):
        """Empty tenant IDs should raise ValueError."""
        with pytest.raises(ValueError, match="invalid tenant_id"):
            FederatedEngine._sanitize_tenant_id("")
        with pytest.raises(ValueError, match="invalid tenant_id"):
            FederatedEngine._sanitize_tenant_id("   ")

    def test_max_length_enforced(self):
        """IDs longer than 128 chars should be truncated."""
        long_id = "a" * 200
        result = FederatedEngine._sanitize_tenant_id(long_id)
        assert len(result) == 128


class TestEngineFactory:
    """Tests for get_engine() factory function."""

    @patch("cortex.federation.FEDERATION_MODE", "single")
    def test_single_mode_returns_cortex_engine(self):
        """Single mode should return standard CortexEngine."""
        engine = get_engine(auto_embed=False)
        from cortex.engine import CortexEngine

        assert isinstance(engine, CortexEngine)

    @patch("cortex.federation.FEDERATION_MODE", "federated")
    def test_federated_mode_returns_federated_engine(self):
        """Federated mode should return FederatedEngine."""
        engine = get_engine(auto_embed=False)
        assert isinstance(engine, FederatedEngine)

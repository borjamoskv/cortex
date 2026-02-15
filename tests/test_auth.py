"""
CORTEX v4.0 — Auth Tests.

Tests for API key creation, authentication, and revocation.
"""

import os
import tempfile

import pytest

from cortex.auth import AuthManager


@pytest.fixture
def auth():
    db = tempfile.mktemp(suffix=".db")
    manager = AuthManager(db)
    yield manager
    os.unlink(db)


class TestKeyCreation:
    def test_create_key(self, auth):
        raw_key, api_key = auth.create_key("test-key")
        assert raw_key.startswith("ctx_")
        assert api_key.name == "test-key"
        assert api_key.is_active is True

    def test_key_prefix_stored(self, auth):
        raw_key, api_key = auth.create_key("prefix-test")
        assert api_key.key_prefix == raw_key[:12]

    def test_custom_permissions(self, auth):
        _, api_key = auth.create_key("readonly", permissions=["read"])
        assert api_key.permissions == ["read"]

    def test_custom_tenant(self, auth):
        _, api_key = auth.create_key("tenant-test", tenant_id="acme-corp")
        assert api_key.tenant_id == "acme-corp"


class TestAuthentication:
    def test_valid_key(self, auth):
        raw_key, _ = auth.create_key("auth-test")
        result = auth.authenticate(raw_key)
        assert result.authenticated is True
        assert result.key_name == "auth-test"

    def test_invalid_key(self, auth):
        result = auth.authenticate("ctx_invalid_key_12345")
        assert result.authenticated is False

    def test_bad_format(self, auth):
        result = auth.authenticate("not-a-cortex-key")
        assert result.authenticated is False
        assert "format" in result.error.lower()

    def test_empty_key(self, auth):
        result = auth.authenticate("")
        assert result.authenticated is False


class TestRevocation:
    def test_revoke_key(self, auth):
        raw_key, api_key = auth.create_key("revoke-test")
        assert auth.revoke_key(api_key.id) is True
        result = auth.authenticate(raw_key)
        assert result.authenticated is False

    def test_revoke_nonexistent(self, auth):
        assert auth.revoke_key(99999) is False


class TestListKeys:
    def test_list_all(self, auth):
        auth.create_key("key-1")
        auth.create_key("key-2")
        keys = auth.list_keys()
        assert len(keys) == 2

    def test_list_by_tenant(self, auth):
        auth.create_key("t1", tenant_id="alpha")
        auth.create_key("t2", tenant_id="beta")
        alpha_keys = auth.list_keys(tenant_id="alpha")
        assert len(alpha_keys) == 1
        assert alpha_keys[0].tenant_id == "alpha"

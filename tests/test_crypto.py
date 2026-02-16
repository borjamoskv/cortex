"""Tests for L3 Vaults."""
import os
import pytest
from cortex.crypto import Vault

try:
    import cryptography
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

@pytest.mark.skipif(not HAS_CRYPTO, reason="cryptography not installed")
def test_vault_encryption():
    # usage: Vault(key_bytes)
    key_b64 = Vault.generate_key()
    import base64
    key = base64.b64decode(key_b64)
    
    vault = Vault(key)
    assert vault.is_available
    
    original = "Secret Information"
    encrypted = vault.encrypt(original)
    
    assert encrypted != original
    
    decrypted = vault.decrypt(encrypted)
    assert decrypted == original

@pytest.mark.skipif(not HAS_CRYPTO, reason="cryptography not installed")
def test_vault_env_key(monkeypatch):
    key_b64 = Vault.generate_key()
    monkeypatch.setenv("CORTEX_VAULT_KEY", key_b64)
    
    vault = Vault()
    assert vault.is_available
    
    res = vault.decrypt(vault.encrypt("test"))
    assert res == "test"

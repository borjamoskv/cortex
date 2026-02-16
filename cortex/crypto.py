"""Cryptographic Vaults.

Implements L3 Application-Level Encryption using AES-GCM.
"""
import base64
import os
from typing import Optional

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    AESGCM = None

class Vault:
    """Secure Vault for storing sensitive facts."""
    
    def __init__(self, key: Optional[bytes] = None):
        if not AESGCM:
            self._key = None
            return
            
        if key:
            self._key = key
        else:
            # Load from env or generate
            env_key = os.environ.get("CORTEX_VAULT_KEY")
            if env_key:
                try:
                    self._key = base64.b64decode(env_key)
                except Exception:
                     # Fallback if invalid base64? No, invalid key is fatal.
                    self._key = None # Or raise
            else:
                # For dev/testing, generate one if none exists? 
                # Better: Allow no key (disabled encryption)
                self._key = None

    @property
    def is_available(self) -> bool:
        return AESGCM is not None and self._key is not None

    def encrypt(self, data: str) -> str:
        """Encrypt string using AES-GCM."""
        if not self.is_available:
            raise RuntimeError("Encryption not available (missing key or library)")
            
        aesgcm = AESGCM(self._key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data.encode("utf-8"), None)
        
        # Format: base64(nonce + ciphertext)
        return base64.b64encode(nonce + ciphertext).decode("utf-8")

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string using AES-GCM."""
        if not self.is_available:
            raise RuntimeError("Encryption not available (missing key or library)")
            
        try:
            raw = base64.b64decode(encrypted_data)
            nonce = raw[:12]
            ciphertext = raw[12:]
            
            aesgcm = AESGCM(self._key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

    @staticmethod
    def generate_key() -> str:
        """Generate a new secure key (base64 encoded)."""
        if not AESGCM:
            raise ImportError("cryptography library not installed")
        key = AESGCM.generate_key(bit_length=256)
        return base64.b64encode(key).decode("utf-8")

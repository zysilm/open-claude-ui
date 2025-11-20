"""API key encryption service using Fernet (AES-128)."""

import os
from cryptography.fernet import Fernet
from typing import Optional


class KeyEncryptionService:
    """Service for encrypting and decrypting API keys."""

    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption service with master key.

        Args:
            master_key: Base64-encoded 32-byte key. If not provided, reads from environment.
        """
        key = master_key or os.getenv("MASTER_ENCRYPTION_KEY")

        if not key:
            raise ValueError(
                "MASTER_ENCRYPTION_KEY environment variable not set. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        try:
            self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            raise ValueError(f"Invalid MASTER_ENCRYPTION_KEY: {e}")

    def encrypt(self, plaintext: str) -> bytes:
        """
        Encrypt a plaintext API key.

        Args:
            plaintext: The API key to encrypt

        Returns:
            Encrypted bytes
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")

        return self.cipher.encrypt(plaintext.encode())

    def decrypt(self, encrypted: bytes) -> str:
        """
        Decrypt an encrypted API key.

        Args:
            encrypted: The encrypted API key bytes

        Returns:
            Decrypted plaintext API key
        """
        if not encrypted:
            raise ValueError("Cannot decrypt empty bytes")

        try:
            return self.cipher.decrypt(encrypted).decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt API key: {e}")

    @staticmethod
    def generate_master_key() -> str:
        """
        Generate a new master encryption key.

        Returns:
            Base64-encoded 32-byte key suitable for Fernet
        """
        return Fernet.generate_key().decode()


# Global encryption service instance
_encryption_service: Optional[KeyEncryptionService] = None


def get_encryption_service() -> KeyEncryptionService:
    """
    Get or create the global encryption service instance.

    Returns:
        KeyEncryptionService instance
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = KeyEncryptionService()
    return _encryption_service

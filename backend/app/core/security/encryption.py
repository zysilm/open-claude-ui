"""API key encryption service using Fernet (AES-128)."""

import os
import sys
from cryptography.fernet import Fernet
from typing import Optional


class KeyEncryptionService:
    """Service for encrypting and decrypting API keys."""

    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption service with master key.

        Args:
            master_key: Base64-encoded 32-byte key. If not provided, reads from environment.
                        In development mode, auto-generates a key if not set.
        """
        key = master_key or os.getenv("MASTER_ENCRYPTION_KEY")

        if not key:
            # Auto-generate key for development convenience
            key = self._auto_generate_key()
            if not key:
                raise ValueError(
                    "MASTER_ENCRYPTION_KEY environment variable not set.\n"
                    "Please set up your .env file:\n"
                    "  1. cp .env.example .env\n"
                    "  2. Generate a key: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'\n"
                    "  3. Add the key to .env as MASTER_ENCRYPTION_KEY=<your-key>"
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

    def _auto_generate_key(self) -> Optional[str]:
        """
        Auto-generate and save a master key to .env file for development convenience.

        Returns:
            Generated key if successful, None otherwise
        """
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
        env_path = os.path.abspath(env_path)

        # Generate a new key
        new_key = Fernet.generate_key().decode()

        try:
            # Check if .env exists
            if os.path.exists(env_path):
                # Read existing content
                with open(env_path, "r") as f:
                    content = f.read()

                # Check if MASTER_ENCRYPTION_KEY is already there but empty
                if "MASTER_ENCRYPTION_KEY=" in content:
                    # Replace empty or placeholder value
                    lines = content.split("\n")
                    new_lines = []
                    for line in lines:
                        if line.startswith("MASTER_ENCRYPTION_KEY="):
                            new_lines.append(f"MASTER_ENCRYPTION_KEY={new_key}")
                        else:
                            new_lines.append(line)
                    content = "\n".join(new_lines)
                else:
                    # Append the key
                    content += f"\nMASTER_ENCRYPTION_KEY={new_key}\n"

                with open(env_path, "w") as f:
                    f.write(content)
            else:
                # Create new .env file with the key
                with open(env_path, "w") as f:
                    f.write("# Auto-generated .env file\n")
                    f.write(f"MASTER_ENCRYPTION_KEY={new_key}\n")

            print(f"Auto-generated MASTER_ENCRYPTION_KEY and saved to {env_path}")
            return new_key

        except (IOError, OSError) as e:
            print(f"Warning: Could not auto-save encryption key to .env: {e}", file=sys.stderr)
            return None

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

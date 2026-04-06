"""Fernet-based symmetric encryption for tenant credentials.

All secrets are encrypted before being written to the database.
The ENCRYPTION_KEY env var must be a URL-safe base64-encoded 32-byte key.
Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from cryptography.fernet import Fernet
from .config import settings


def _cipher() -> Fernet:
    return Fernet(settings.encryption_key.encode())


def encrypt(value: str) -> str:
    """Return an encrypted, base64-encoded token."""
    return _cipher().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    """Decrypt a token previously produced by encrypt()."""
    return _cipher().decrypt(value.encode()).decode()

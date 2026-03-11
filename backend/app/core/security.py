"""
Security utilities.

Provides password hashing (Argon2id), session token generation,
and cookie configuration constants.
"""

import secrets
from argon2 import PasswordHasher
from argon2.exceptions import (
    HashingError,
    VerificationError,
    VerifyMismatchError,
    InvalidHashError,
)

# Argon2id hasher with secure defaults
_hasher = PasswordHasher(
    time_cost=3,       # Number of iterations
    memory_cost=65536,  # 64 MB memory usage
    parallelism=4,      # Parallel threads
    hash_len=32,        # Output hash length
    salt_len=16,        # Salt length
)

# Session token length (bytes) — 32 bytes = 256 bits of entropy
SESSION_TOKEN_BYTES = 32


def hash_password(password: str) -> str:
    """Hash a password using Argon2id.

    Args:
        password: The plaintext password to hash.

    Returns:
        The Argon2id hash string.

    Raises:
        HashingError: If hashing fails unexpectedly.
    """
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against an Argon2id hash.

    Args:
        password: The plaintext password to check.
        password_hash: The stored Argon2id hash.

    Returns:
        True if the password matches, False otherwise.
    """
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def check_needs_rehash(password_hash: str) -> bool:
    """Check if a password hash needs to be re-hashed.

    This is useful when upgrading hashing parameters — existing
    hashes with old parameters are detected and can be re-hashed
    on the next successful login.

    Args:
        password_hash: The stored hash string.

    Returns:
        True if the hash should be regenerated.
    """
    return _hasher.check_needs_rehash(password_hash)


def generate_session_token() -> str:
    """Generate a cryptographically secure session token.

    Returns:
        A URL-safe random string with 256 bits of entropy.
    """
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)

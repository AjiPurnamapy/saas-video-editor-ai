"""
Login brute-force protection module.

M-06 FIX: Implements account lockout after too many failed login attempts.
Uses Redis counters with TTL to track failed attempts per email and IP.

Lockout rules:
- 10 failed attempts within 5 minutes → 15 minute lockout
- Applies to both email (protects specific accounts) and IP (blocks scanners)
- Counters reset on successful login

S-03 FIX: Identifiers are hashed before use as Redis keys to avoid
storing PII (email addresses) in the Redis key namespace.
"""

import hashlib
import logging

from app.core.session_manager import _redis_client

logger = logging.getLogger(__name__)

LOCKOUT_PREFIX = "login_lockout:"
ATTEMPT_PREFIX = "login_attempts:"
MAX_ATTEMPTS = 10
LOCKOUT_DURATION = 900     # 15 minutes
ATTEMPT_WINDOW = 300       # Count within 5-minute window


def _hash_identifier(identifier: str) -> str:
    """Hash an identifier to avoid storing PII in Redis key names.

    S-03 FIX: Email addresses and IPs are hashed with SHA-256
    before being used as Redis key components.

    Args:
        identifier: Email address or IP address.

    Returns:
        First 32 hex chars of the SHA-256 hash.
    """
    return hashlib.sha256(identifier.lower().strip().encode()).hexdigest()[:32]


def record_failed_attempt(identifier: str) -> tuple[int, bool]:
    """Record a failed login attempt for an identifier.

    Args:
        identifier: Email address or IP address.

    Returns:
        Tuple of (attempt_count, is_now_locked_out).
    """
    hashed = _hash_identifier(identifier)
    attempt_key = f"{ATTEMPT_PREFIX}{hashed}"

    pipe = _redis_client.pipeline()
    pipe.incr(attempt_key)
    pipe.expire(attempt_key, ATTEMPT_WINDOW)
    results = pipe.execute()

    attempts = results[0]

    if attempts >= MAX_ATTEMPTS:
        lockout_key = f"{LOCKOUT_PREFIX}{hashed}"
        _redis_client.setex(lockout_key, LOCKOUT_DURATION, "1")
        logger.warning(
            "Account locked out: identifier_hash=%s attempts=%d",
            hashed[:12], attempts,
        )
        return attempts, True

    return attempts, False


def is_locked_out(identifier: str) -> bool:
    """Check if an identifier is currently locked out.

    Args:
        identifier: Email address or IP address.

    Returns:
        True if locked out.
    """
    lockout_key = f"{LOCKOUT_PREFIX}{_hash_identifier(identifier)}"
    return _redis_client.exists(lockout_key) > 0


def clear_failed_attempts(identifier: str) -> None:
    """Clear failed attempt counters after a successful login.

    Args:
        identifier: Email address or IP address.
    """
    hashed = _hash_identifier(identifier)
    _redis_client.delete(f"{ATTEMPT_PREFIX}{hashed}")
    _redis_client.delete(f"{LOCKOUT_PREFIX}{hashed}")

"""
Login brute-force protection module.

M-06 FIX: Implements account lockout after too many failed login attempts.
Uses Redis counters with TTL to track failed attempts per email and IP.

Lockout rules:
- 10 failed attempts within 5 minutes → 15 minute lockout
- Applies to both email (protects specific accounts) and IP (blocks scanners)
- Counters reset on successful login
"""

import logging

from app.core.session_manager import _redis_client

logger = logging.getLogger(__name__)

LOCKOUT_PREFIX = "login_lockout:"
ATTEMPT_PREFIX = "login_attempts:"
MAX_ATTEMPTS = 10
LOCKOUT_DURATION = 900     # 15 minutes
ATTEMPT_WINDOW = 300       # Count within 5-minute window


def record_failed_attempt(identifier: str) -> tuple[int, bool]:
    """Record a failed login attempt for an identifier.

    Args:
        identifier: Email address or IP address.

    Returns:
        Tuple of (attempt_count, is_now_locked_out).
    """
    attempt_key = f"{ATTEMPT_PREFIX}{identifier}"

    pipe = _redis_client.pipeline()
    pipe.incr(attempt_key)
    pipe.expire(attempt_key, ATTEMPT_WINDOW)
    results = pipe.execute()

    attempts = results[0]

    if attempts >= MAX_ATTEMPTS:
        lockout_key = f"{LOCKOUT_PREFIX}{identifier}"
        _redis_client.setex(lockout_key, LOCKOUT_DURATION, "1")
        logger.warning(
            "Account locked out: identifier=%s attempts=%d",
            identifier[:20], attempts,
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
    lockout_key = f"{LOCKOUT_PREFIX}{identifier}"
    return _redis_client.exists(lockout_key) > 0


def clear_failed_attempts(identifier: str) -> None:
    """Clear failed attempt counters after a successful login.

    Args:
        identifier: Email address or IP address.
    """
    _redis_client.delete(f"{ATTEMPT_PREFIX}{identifier}")
    _redis_client.delete(f"{LOCKOUT_PREFIX}{identifier}")

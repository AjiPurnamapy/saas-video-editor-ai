"""
Session manager module.

Handles Redis-backed session CRUD operations. Each session is stored
as a Redis hash with automatic TTL-based expiration.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis

from app.config import get_settings

settings = get_settings()

# Redis connection pool — explicit config for production stability
_pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=20,
    decode_responses=True,
    socket_timeout=5,
    socket_connect_timeout=5,
)
_redis_client = redis.Redis(connection_pool=_pool)

# Key prefix to namespace session keys in Redis
SESSION_PREFIX = "session:"

# H-04 FIX: Prefix for per-user session index (Redis SET)
SESSION_USER_INDEX_PREFIX = "user_sessions:"


def _session_key(session_id: str) -> str:
    """Build the Redis key for a session.

    Args:
        session_id: The unique session token.

    Returns:
        The namespaced Redis key string.
    """
    return f"{SESSION_PREFIX}{session_id}"


def create_session(
    session_id: str,
    user_id: str,
    ip_address: str = "",
    user_agent: str = "",
) -> None:
    """Create a new session in Redis.

    Args:
        session_id: Unique session token (from security.generate_session_token).
        user_id: The UUID of the authenticated user.
        ip_address: Client IP address for audit logging.
        user_agent: Client User-Agent header for audit logging.
    """
    session_data = {
        "user_id": user_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    key = _session_key(session_id)
    _redis_client.set(
        key,
        json.dumps(session_data),
        ex=settings.session_max_age_seconds,
    )

    # H-04 FIX: Index session under user for bulk invalidation
    user_index_key = f"{SESSION_USER_INDEX_PREFIX}{user_id}"
    _redis_client.sadd(user_index_key, session_id)
    _redis_client.expire(user_index_key, settings.session_max_age_seconds)


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a session from Redis.

    Args:
        session_id: The session token to look up.

    Returns:
        A dictionary of session data, or None if the session
        does not exist or has expired.
    """
    key = _session_key(session_id)
    data = _redis_client.get(key)
    if data is None:
        return None
    return json.loads(data)


def delete_session(session_id: str) -> None:
    """Delete a session from Redis (logout).

    Args:
        session_id: The session token to revoke.
    """
    key = _session_key(session_id)
    _redis_client.delete(key)


def refresh_session(session_id: str) -> bool:
    """Refresh the TTL on an existing session (sliding expiration).

    S-18 FIX: Also refreshes the user session index TTL so that
    delete_all_user_sessions() can still find long-lived sessions.

    Args:
        session_id: The session token to refresh.

    Returns:
        True if the session exists and was refreshed, False otherwise.
    """
    key = _session_key(session_id)
    refreshed = bool(_redis_client.expire(key, settings.session_max_age_seconds))
    if refreshed:
        # Refresh user index TTL too
        data = get_session(session_id)
        if data and "user_id" in data:
            user_index_key = f"{SESSION_USER_INDEX_PREFIX}{data['user_id']}"
            _redis_client.expire(user_index_key, settings.session_max_age_seconds)
    return refreshed


def delete_all_user_sessions(user_id: str) -> int:
    """Invalidate ALL active sessions for a user.

    H-04 FIX: Called when:
    - User changes password (kills attacker sessions)
    - User requests "logout all devices"
    - Admin forces account lockout

    Args:
        user_id: The user's UUID.

    Returns:
        Number of sessions invalidated.
    """
    user_index_key = f"{SESSION_USER_INDEX_PREFIX}{user_id}"
    session_ids = _redis_client.smembers(user_index_key)

    if not session_ids:
        return 0

    pipe = _redis_client.pipeline()
    for sid in session_ids:
        pipe.delete(_session_key(sid))
    pipe.delete(user_index_key)
    pipe.execute()

    return len(session_ids)

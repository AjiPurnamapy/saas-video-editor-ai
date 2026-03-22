"""
Rate limiter module.

Provides a shared slowapi Limiter instance used across route modules.
Extracted to its own module to avoid circular imports between
main.py and route files.

SECURITY (C-02 FIX):
- Rate limits per authenticated user when possible, falls back to IP
- Prevents resource exhaustion from upload/job start spam
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
import os

# Disable limiter entirely during tests by checking an env var we'll set in conftest
_is_testing = os.getenv("TESTING") == "1"


def get_user_id_or_ip(request: Request) -> str:
    """Rate limit per user if authenticated, per IP otherwise.

    This is more fair than IP-only limiting because:
    - Multiple users behind a corporate NAT share one IP
    - A single user with multiple IPs (VPN) could bypass IP-only limits
    """
    # Check if the request has a current_user set by the auth dependency
    user = getattr(request.state, "current_user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"
    return get_remote_address(request)


# Shared limiter instance — imported by route modules and main.py
# S-11 FIX: headers_enabled returns X-RateLimit-* headers to clients
limiter = Limiter(
    key_func=get_user_id_or_ip,
    enabled=not _is_testing,
    headers_enabled=True,
)

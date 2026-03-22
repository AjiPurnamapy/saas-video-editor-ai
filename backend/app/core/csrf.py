"""
CSRF protection module.

H-01 FIX: Implements the Double Submit Cookie pattern.
The CSRF token is stored in a non-HTTPOnly cookie (readable by JavaScript)
and must be sent back in the X-CSRF-Token header for state-changing requests.

An attacker from another domain cannot read the cookie value (Same-Origin Policy),
so they cannot include the correct header value in a forged request.
"""

import hmac
import secrets

from fastapi import HTTPException, Request, status

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"

# Paths exempt from CSRF validation
# - login/register: user doesn't have a CSRF token yet
# - verify/forgot/reset: accessed from email links (no session cookie)
# - download: token-based auth, no session needed
_CSRF_EXEMPT_PATHS = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/verify-email",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
    "/api/auth/resend-verification",
}

# Paths exempt via prefix matching (for dynamic path segments)
_CSRF_EXEMPT_PREFIXES = (
    "/api/outputs/download/",
)


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response, token: str, settings) -> None:
    """Set the CSRF cookie on a response.

    The cookie is intentionally NOT HTTPOnly so that JavaScript
    can read it and include it in request headers.

    Args:
        response: FastAPI Response object.
        token: The CSRF token value.
        settings: Application settings (for cookie config).
    """
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,  # Must be readable by JS to include in header
        secure=settings.cookie_secure,
        samesite="strict",
        max_age=settings.session_max_age_seconds,
        path="/",
    )


def verify_csrf_token(request: Request) -> None:
    """Verify the CSRF token using the Double Submit Cookie pattern.

    Compares the cookie value with the header value using a
    constant-time comparison to prevent timing attacks.

    Args:
        request: The incoming FastAPI request.

    Raises:
        HTTPException: If the CSRF token is missing or invalid.
    """
    # Skip verification for safe methods
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # Skip verification for exempt paths (login, register, email flows)
    if request.url.path in _CSRF_EXEMPT_PATHS:
        return

    # Skip verification for exempt prefixes (e.g., /api/outputs/download/{token})
    if any(request.url.path.startswith(p) for p in _CSRF_EXEMPT_PREFIXES):
        return

    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)

    if not cookie_token or not header_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing",
        )

    # Constant-time comparison prevents timing attack
    if not hmac.compare_digest(cookie_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token invalid",
        )

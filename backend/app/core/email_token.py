"""
Email token module.

Generates and verifies time-limited tokens for email verification
and password reset flows. Uses itsdangerous with separate salts
to prevent token cross-use between different operations.
"""

import logging
from typing import Optional

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.config import get_settings

logger = logging.getLogger(__name__)

# Token expiry durations
VERIFICATION_TOKEN_MAX_AGE = 86400  # 24 hours
RESET_TOKEN_MAX_AGE = 3600          # 1 hour

# Salts to namespace token types
_VERIFY_SALT = "email-verification"
_RESET_SALT = "password-reset"


def _get_serializer() -> URLSafeTimedSerializer:
    """Get a serializer using the app's secret key."""
    settings = get_settings()
    return URLSafeTimedSerializer(settings.secret_key)


def generate_verification_token(user_id: str) -> str:
    """Generate a signed email verification token.

    Args:
        user_id: The user UUID to verify.

    Returns:
        A URL-safe signed token string (valid for 24 hours).
    """
    serializer = _get_serializer()
    token = serializer.dumps({"user_id": user_id}, salt=_VERIFY_SALT)
    logger.debug("Verification token generated: user=%s", user_id)
    return token


def verify_verification_token(token: str) -> Optional[str]:
    """Verify an email verification token.

    Args:
        token: The signed token string.

    Returns:
        The user_id if valid, None if invalid/expired.
    """
    serializer = _get_serializer()
    try:
        payload = serializer.loads(
            token, salt=_VERIFY_SALT, max_age=VERIFICATION_TOKEN_MAX_AGE,
        )
        return payload.get("user_id")
    except SignatureExpired:
        logger.warning("Verification token expired")
        return None
    except BadSignature:
        logger.warning("Verification token invalid signature")
        return None


def generate_reset_token(user_id: str) -> str:
    """Generate a signed password reset token.

    Args:
        user_id: The user UUID requesting the reset.

    Returns:
        A URL-safe signed token string (valid for 1 hour).
    """
    serializer = _get_serializer()
    token = serializer.dumps({"user_id": user_id}, salt=_RESET_SALT)
    logger.debug("Reset token generated: user=%s", user_id)
    return token


def verify_reset_token(token: str) -> Optional[str]:
    """Verify a password reset token.

    Args:
        token: The signed token string.

    Returns:
        The user_id if valid, None if invalid/expired.
    """
    serializer = _get_serializer()
    try:
        payload = serializer.loads(
            token, salt=_RESET_SALT, max_age=RESET_TOKEN_MAX_AGE,
        )
        return payload.get("user_id")
    except SignatureExpired:
        logger.warning("Reset token expired")
        return None
    except BadSignature:
        logger.warning("Reset token invalid signature")
        return None

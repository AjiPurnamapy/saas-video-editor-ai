"""
Signed URL token module.

Generates and verifies time-limited, cryptographically signed tokens
for secure output video downloads. Clients never see internal file paths —
they receive an opaque token that the server maps back to the file.

Uses itsdangerous.URLSafeTimedSerializer with the app's secret_key.
"""

import logging
from typing import Optional

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.config import get_settings

logger = logging.getLogger(__name__)

# Token validity duration in seconds (1 hour)
DOWNLOAD_TOKEN_MAX_AGE = 3600

# Salt to namespace download tokens (prevents reuse as other token types)
_DOWNLOAD_SALT = "output-download"


def _get_serializer() -> URLSafeTimedSerializer:
    """Get a serializer using the app's secret key."""
    settings = get_settings()
    return URLSafeTimedSerializer(settings.secret_key)


def generate_download_token(output_id: str, user_id: str) -> str:
    """Generate a signed download token for an output.

    Args:
        output_id: The output UUID to grant access to.
        user_id: The user UUID requesting the download.

    Returns:
        A URL-safe signed token string.
    """
    serializer = _get_serializer()
    payload = {"output_id": output_id, "user_id": user_id}
    token = serializer.dumps(payload, salt=_DOWNLOAD_SALT)
    logger.debug("Download token generated: output=%s user=%s", output_id, user_id)
    return token


def verify_download_token(
    token: str,
    max_age: int = DOWNLOAD_TOKEN_MAX_AGE,
) -> Optional[dict]:
    """Verify and decode a signed download token.

    Args:
        token: The signed token string.
        max_age: Maximum token age in seconds (default: 1 hour).

    Returns:
        Dict with {output_id, user_id} if valid, None if invalid/expired.
    """
    serializer = _get_serializer()
    try:
        payload = serializer.loads(token, salt=_DOWNLOAD_SALT, max_age=max_age)
        return payload
    except SignatureExpired:
        logger.warning("Download token expired")
        return None
    except BadSignature:
        logger.warning("Download token invalid signature")
        return None

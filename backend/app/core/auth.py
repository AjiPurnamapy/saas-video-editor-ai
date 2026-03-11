"""
Authentication dependency module.

Provides FastAPI dependencies for extracting and validating the
current user from the session cookie on each request.
"""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.session_manager import get_session
from app.database import get_db
from app.models.user import User

settings = get_settings()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency — extracts the authenticated user from the session.

    Reads the session cookie from the request, validates it against
    Redis, and fetches the corresponding user from the database.

    Args:
        request: The incoming FastAPI Request (provides cookies).
        db: Database session (injected via Depends).

    Returns:
        The authenticated User model instance.

    Raises:
        HTTPException: 401 if the session cookie is missing, the
                       session has expired, or the user no longer exists.
    """
    session_id = request.cookies.get(settings.session_cookie_name)
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated — session cookie missing",
        )

    # Look up session in Redis
    session_data = get_session(session_id)
    if session_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
        )

    # Fetch user from database
    user_id = session_data.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user

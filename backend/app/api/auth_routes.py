"""
Authentication API routes.

Endpoints for user registration, login, logout, and retrieving
the current authenticated user.

SECURITY:
- Rate limiting applied to login (5/min) and register (3/min)
- HTTPOnly/Secure/SameSite cookies for session management
- Structured logging for all auth events
"""

import logging

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.auth import get_current_user
from app.core.csrf import generate_csrf_token, set_csrf_cookie
from app.database import get_db
from app.core.rate_limiter import limiter
from app.models.user import User
from app.schemas.user_schema import (
    ChangePasswordRequest,
    MessageResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
@limiter.limit("3/minute")
def register(
    request: Request,
    data: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Register a new user account.

    Rate limited to 3 requests per minute per IP.

    Creates a user with the given email and password.
    The password is hashed using Argon2id before storage.

    Args:
        request: FastAPI request (required by slowapi limiter).
        data: Registration request body.
        db: Database session (injected).

    Returns:
        The newly created user's public information.
    """
    service = AuthService(db)
    user = service.register(data)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=UserResponse,
    summary="Login with credentials",
)
@limiter.limit("5/minute")
def login(
    data: UserLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Authenticate a user and create a session.

    Rate limited to 5 requests per minute per IP.

    On success, sets an HTTPOnly session cookie and returns
    the user's public information.

    Args:
        data: Login request body.
        request: FastAPI request (for IP/user-agent + rate limiting).
        response: FastAPI response (for setting cookies).
        db: Database session (injected).

    Returns:
        The authenticated user's public information.
    """
    service = AuthService(db)
    ip_address = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "")

    user, session_token = service.login(data, ip_address, user_agent)

    # Set HTTPOnly session cookie
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_max_age_seconds,
        domain=settings.cookie_domain if settings.app_env != "development" else None,
        path="/",
    )

    # H-01 FIX: Set CSRF cookie (readable by JS for header inclusion)
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token, settings)

    return UserResponse.model_validate(user)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout and destroy session",
)
def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Logout the current user.

    Destroys the Redis session and clears the session cookie.

    Args:
        request: FastAPI request (for reading session cookie).
        response: FastAPI response (for clearing cookie).
        current_user: The authenticated user (injected).

    Returns:
        A confirmation message.
    """
    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id:
        AuthService.logout(session_id)

    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )

    logger.info("Logout: user=%s", current_user.id)
    return MessageResponse(message="Logged out successfully")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the currently authenticated user's information.

    Args:
        current_user: The authenticated user (injected via session).

    Returns:
        The user's public information.
    """
    return UserResponse.model_validate(current_user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password",
)
@limiter.limit("5/minute")
def change_password(
    request: Request,
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Change the current user's password.

    H-04 FIX: After changing the password, ALL active sessions are
    invalidated — including any created by an attacker.
    The user must log in again with the new password.
    Rate limited to 5 requests per minute.

    Args:
        request: FastAPI request (required by slowapi limiter).
        data: Old and new password.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        A confirmation message.
    """
    service = AuthService(db)
    service.change_password(
        user_id=current_user.id,
        old_password=data.old_password,
        new_password=data.new_password,
    )
    logger.info("Password changed: user=%s", current_user.id)
    return MessageResponse(message="Password changed. Please log in again.")

"""
Authentication API routes.

Endpoints for user registration, login, logout, email verification,
password reset, and retrieving the current authenticated user.

SECURITY:
- Rate limiting applied to login (5/min) and register (3/min)
- HTTPOnly/Secure/SameSite cookies for session management
- Structured logging for all auth events
- Email verification required for new accounts
- Password reset via signed time-limited tokens
"""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.auth import get_current_user
from app.core.csrf import generate_csrf_token, set_csrf_cookie
from app.database import get_db
from app.core.rate_limiter import limiter
from app.models.user import User
from app.schemas.user_schema import (
    ChangePasswordRequest,
    EmailTokenRequest,
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()
logger = logging.getLogger(__name__)


async def _send_email_bg(coro_func, *args) -> None:
    """Fire-and-forget email sending for background tasks.

    S-08 FIX: Emails are sent in the background to avoid blocking
    the Uvicorn thread during SMTP connection.
    """
    try:
        await coro_func(*args)
    except Exception as exc:
        logger.warning("Background email failed: %s", str(exc))


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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Register a new user account.

    Rate limited to 3 requests per minute per IP.

    Creates a user with the given email and password.
    The password is hashed using Argon2id before storage.
    A verification email is sent in the background.

    Args:
        request: FastAPI request (required by slowapi limiter).
        data: Registration request body.
        background_tasks: FastAPI background tasks manager.
        db: Database session (injected).

    Returns:
        The newly created user's public information.
    """
    service = AuthService(db)
    user = service.register(data)

    # S-08 FIX: Send verification email in background (non-blocking)
    token = service.generate_verification_token(str(user.id))
    from app.services.email_service import send_verification_email
    background_tasks.add_task(_send_email_bg, send_verification_email, user.email, token)

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
        domain=settings.cookie_domain if settings.app_env == "production" else None,
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


# --- Email Verification ---

@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify email with token",
)
@limiter.limit("10/minute")
def verify_email(
    request: Request,
    data: EmailTokenRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Verify a user's email address using the token sent via email.

    Rate limited to 10 requests per minute.

    Args:
        request: FastAPI request (required by slowapi limiter).
        data: Request body with the verification token.
        db: Database session (injected).

    Returns:
        A confirmation message.
    """
    service = AuthService(db)
    service.verify_email(data.token)
    return MessageResponse(message="Email verified successfully.")


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Resend verification email",
)
@limiter.limit("3/minute")
def resend_verification(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Resend the email verification link to the current user.

    Rate limited to 3 requests per minute.

    Args:
        request: FastAPI request (required by slowapi limiter).
        background_tasks: FastAPI background tasks manager.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        A confirmation message.
    """
    if current_user.is_email_verified:
        return MessageResponse(message="Email is already verified.")

    token = AuthService.generate_verification_token(str(current_user.id))
    from app.services.email_service import send_verification_email
    background_tasks.add_task(_send_email_bg, send_verification_email, current_user.email, token)

    return MessageResponse(message="Verification email sent. Check your inbox.")


# --- Password Reset ---

@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset",
)
@limiter.limit("5/minute")
def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Request a password reset link via email.

    Always returns 200 OK regardless of whether the email exists,
    to prevent user enumeration attacks.

    Rate limited to 5 requests per minute.

    Args:
        request: FastAPI request (required by slowapi limiter).
        data: Request body with the email address.
        background_tasks: FastAPI background tasks manager.
        db: Database session (injected).

    Returns:
        A generic confirmation message.
    """
    service = AuthService(db)
    token = service.request_password_reset(data.email)

    if token:
        from app.services.email_service import send_password_reset_email
        background_tasks.add_task(_send_email_bg, send_password_reset_email, data.email, token)

    # Always return the same message to prevent enumeration
    return MessageResponse(
        message="If an account with that email exists, a password reset link has been sent."
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with token",
)
@limiter.limit("5/minute")
def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Reset a user's password using the token from the reset email.

    After a successful reset, all active sessions are invalidated
    and the user must log in with the new password.

    Rate limited to 5 requests per minute.

    Args:
        request: FastAPI request (required by slowapi limiter).
        data: Request body with the reset token and new password.
        db: Database session (injected).

    Returns:
        A confirmation message.
    """
    service = AuthService(db)
    service.reset_password(data.token, data.new_password)
    return MessageResponse(message="Password reset successful. Please log in with your new password.")

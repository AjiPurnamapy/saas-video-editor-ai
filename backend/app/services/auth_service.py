"""
Authentication service.

Business logic for user registration, login, and session management.
All database and security operations are encapsulated here.

SECURITY:
- Failed login attempts are logged for audit trail purposes.
- H-04 FIX: Password change invalidates ALL active sessions.
- M-04 FIX: All auth events are recorded to the audit log.
- M-06 FIX: Account lockout after 10 failed login attempts.
"""

import hashlib
import logging

from sqlalchemy.orm import Session

from app.core.audit_log import audit, AuditAction
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.security import (
    check_needs_rehash,
    hash_password,
    verify_password,
    generate_session_token,
)
from app.core.session_manager import create_session, delete_session, delete_all_user_sessions
from app.models.user import User
from app.schemas.user_schema import UserRegisterRequest, UserLoginRequest

logger = logging.getLogger(__name__)


def _hash_pii(value: str) -> str:
    """L-03 FIX: Hash PII for logging — correlatable but not plaintext."""
    return hashlib.sha256(value.encode()).hexdigest()[:16]


class AuthService:
    """Encapsulates authentication business logic."""

    def __init__(self, db: Session) -> None:
        """Initialize AuthService with a database session.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db

    def register(self, data: UserRegisterRequest) -> User:
        """Register a new user account.

        Validates that the email is not already taken, hashes the
        password with Argon2id, and persists the new user.

        Args:
            data: Registration request with email and password.

        Returns:
            The newly created User model.

        Raises:
            ConflictError: If the email is already registered.
        """
        existing = self.db.query(User).filter(User.email == data.email).first()
        if existing:
            logger.warning("Registration denied — email_hash=%s", _hash_pii(data.email))
            raise ConflictError("Email already registered")

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        logger.info("User registered: id=%s email_hash=%s", user.id, _hash_pii(user.email))

        # M-04 FIX: Audit log
        audit(
            action=AuditAction.USER_REGISTER,
            user_id=str(user.id),
            resource_type="user",
            success=True,
        )

        return user

    def login(
        self,
        data: UserLoginRequest,
        ip_address: str = "",
        user_agent: str = "",
    ) -> tuple[User, str]:
        """Authenticate a user and create a session.

        Verifies credentials, creates a Redis session, and returns
        the user along with the session token for cookie setting.

        M-06 FIX: Checks lockout status before attempting authentication.
        M-04 FIX: Records audit events for login success/failure.

        Args:
            data: Login request with email and password.
            ip_address: Client IP for session audit trail.
            user_agent: Client User-Agent for session audit trail.

        Returns:
            A tuple of (User, session_token).

        Raises:
            AuthenticationError: If credentials are invalid or account is locked.
        """
        # M-06 FIX: Check lockout BEFORE attempting verification
        try:
            from app.core.login_protection import (
                is_locked_out,
                record_failed_attempt,
                clear_failed_attempts,
            )
            for identifier in [data.email, ip_address]:
                if identifier and is_locked_out(identifier):
                    audit(
                        action=AuditAction.USER_LOCKED_OUT,
                        ip_address=ip_address,
                        success=False,
                        detail={
                            "email_hash": hashlib.sha256(
                                data.email.encode()
                            ).hexdigest()[:16]
                        },
                    )
                    raise AuthenticationError(
                        "Too many failed login attempts. Try again in 15 minutes."
                    )
            _lockout_available = True
        except ImportError:
            _lockout_available = False
        except AuthenticationError:
            raise
        except Exception:
            # Graceful degradation: if Redis is down, skip lockout
            _lockout_available = False

        user = self.db.query(User).filter(User.email == data.email).first()
        if not user or not verify_password(data.password, user.password_hash):
            # M-04 FIX: Audit failed login
            audit(
                action=AuditAction.USER_LOGIN_FAILED,
                ip_address=ip_address,
                success=False,
                detail={
                    "email_hash": hashlib.sha256(
                        data.email.encode()
                    ).hexdigest()[:16],
                },
            )
            # M-06 FIX: Record failed attempt for lockout
            if _lockout_available:
                try:
                    record_failed_attempt(data.email)
                    if ip_address:
                        record_failed_attempt(ip_address)
                except Exception:
                    pass  # Graceful degradation

            logger.warning(
                "Login failed: email_hash=%s ip=%s",
                _hash_pii(data.email), ip_address,
            )
            raise AuthenticationError("Invalid email or password")

        # Re-hash password if Argon2 parameters have been upgraded
        if check_needs_rehash(user.password_hash):
            user.password_hash = hash_password(data.password)
            self.db.commit()
            logger.info("Password rehashed for user: %s", user.id)

        # Create session in Redis
        session_token = generate_session_token()
        create_session(
            session_id=session_token,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # M-06 FIX: Clear failed attempt counters on success
        if _lockout_available:
            try:
                clear_failed_attempts(data.email)
                if ip_address:
                    clear_failed_attempts(ip_address)
            except Exception:
                pass

        # M-04 FIX: Audit successful login
        audit(
            action=AuditAction.USER_LOGIN,
            user_id=str(user.id),
            ip_address=ip_address,
            success=True,
            detail={"user_agent": user_agent[:100]},
        )

        logger.info("Login success: id=%s email_hash=%s ip=%s", user.id, _hash_pii(user.email), ip_address)
        return user, session_token

    @staticmethod
    def logout(session_id: str) -> None:
        """Destroy a user session.

        Args:
            session_id: The session token to revoke.
        """
        delete_session(session_id)
        logger.info("Session destroyed: %s...%s", session_id[:8], session_id[-4:])

    def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> None:
        """Change a user's password and invalidate all sessions.

        H-04 FIX: After changing the password, ALL active sessions
        are destroyed — including any sessions created by an attacker.

        Args:
            user_id: The UUID of the user.
            old_password: Current password for verification.
            new_password: New password to set.

        Raises:
            NotFoundError: If the user does not exist.
            AuthenticationError: If the old password is wrong.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError("User not found")

        if not verify_password(old_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect")

        user.password_hash = hash_password(new_password)
        self.db.commit()

        # CRITICAL: Invalidate ALL sessions — kills attacker sessions
        count = delete_all_user_sessions(user_id)
        logger.info(
            "Password changed, invalidated %d sessions: user=%s",
            count, user_id,
        )

        # M-04 FIX: Audit password change
        audit(
            action=AuditAction.USER_PASSWORD_CHANGE,
            user_id=user_id,
            resource_type="user",
            success=True,
            detail={"sessions_invalidated": count},
        )

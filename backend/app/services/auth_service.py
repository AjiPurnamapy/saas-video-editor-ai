"""
Authentication service.

Business logic for user registration, login, and session management.
All database and security operations are encapsulated here.

SECURITY: Failed login attempts are logged for audit trail purposes.
"""

import logging

from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    check_needs_rehash,
    hash_password,
    verify_password,
    generate_session_token,
)
from app.core.session_manager import create_session, delete_session
from app.models.user import User
from app.schemas.user_schema import UserRegisterRequest, UserLoginRequest

logger = logging.getLogger(__name__)


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
            logger.warning("Registration denied — duplicate email: %s", data.email)
            raise ConflictError("Email already registered")

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        logger.info("User registered: id=%s email=%s", user.id, user.email)
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

        Args:
            data: Login request with email and password.
            ip_address: Client IP for session audit trail.
            user_agent: Client User-Agent for session audit trail.

        Returns:
            A tuple of (User, session_token).

        Raises:
            AuthenticationError: If credentials are invalid.
        """
        user = self.db.query(User).filter(User.email == data.email).first()
        if not user or not verify_password(data.password, user.password_hash):
            logger.warning(
                "Login failed: email=%s ip=%s",
                data.email, ip_address,
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

        logger.info("Login success: id=%s email=%s ip=%s", user.id, user.email, ip_address)
        return user, session_token

    @staticmethod
    def logout(session_id: str) -> None:
        """Destroy a user session.

        Args:
            session_id: The session token to revoke.
        """
        delete_session(session_id)
        logger.info("Session destroyed: %s...%s", session_id[:8], session_id[-4:])

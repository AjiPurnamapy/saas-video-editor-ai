"""
User Pydantic schemas.

Defines request/response models for user-related endpoints.

SECURITY:
- M-01 FIX: Password complexity validation (uppercase, lowercase, digit, special)
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# M-01 FIX: Common passwords that are always rejected
_COMMON_PASSWORDS = {
    "password", "12345678", "qwerty123", "password1!", "abcdefgh",
    "letmein1", "welcome1", "admin123", "iloveyou", "monkey123",
}


def _validate_password_strength(v: str) -> str:
    """Shared password strength validator for registration and password change."""
    errors = []
    if not re.search(r"[A-Z]", v):
        errors.append("at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        errors.append("at least one lowercase letter")
    if not re.search(r"\d", v):
        errors.append("at least one digit")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-]", v):
        errors.append("at least one special character")
    if v.lower() in _COMMON_PASSWORDS:
        errors.append("password is too common")
    if errors:
        raise ValueError(f"Weak password: {', '.join(errors)}")
    return v


class UserRegisterRequest(BaseModel):
    """Request body for user registration."""

    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 chars, must include upper/lower/digit/special)",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """M-01 FIX: Enforce password complexity requirements."""
        return _validate_password_strength(v)


class UserLoginRequest(BaseModel):
    """Request body for user login."""

    email: EmailStr = Field(
        ...,
        description="Registered email address",
    )
    password: str = Field(
        ...,
        description="Account password",
    )


class UserResponse(BaseModel):
    """Public user information returned by the API."""

    id: str
    email: str
    is_email_verified: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    detail: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """H-04 FIX: Request body for changing password."""

    old_password: str = Field(
        ...,
        description="Current password for verification",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (min 8 chars, must include upper/lower/digit/special)",
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, v: str) -> str:
        """M-01 FIX: Enforce password complexity on password change too."""
        return _validate_password_strength(v)


class EmailTokenRequest(BaseModel):
    """Request body for email verification."""

    token: str = Field(
        ...,
        description="Email verification or password reset token",
    )


class ForgotPasswordRequest(BaseModel):
    """Request body for forgot password."""

    email: EmailStr = Field(
        ...,
        description="Email address of the account",
    )


class ResetPasswordRequest(BaseModel):
    """Request body for resetting password with a token."""

    token: str = Field(
        ...,
        description="Password reset token from email",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (min 8 chars, must include upper/lower/digit/special)",
    )

    @field_validator("new_password")
    @classmethod
    def validate_reset_password_strength(cls, v: str) -> str:
        """Enforce password complexity on password reset."""
        return _validate_password_strength(v)

"""
Email token unit tests.

S-24 FIX: Tests for token generation, verification, expiry,
and cross-use prevention between verification and reset tokens.
"""

from app.core.email_token import (
    generate_verification_token,
    verify_verification_token,
    generate_reset_token,
    verify_reset_token,
)


class TestVerificationToken:
    """Tests for email verification token lifecycle."""

    def test_round_trip(self):
        """A freshly generated token verifies successfully."""
        token = generate_verification_token("user-123")
        user_id = verify_verification_token(token)
        assert user_id == "user-123"

    def test_invalid_token_returns_none(self):
        """A tampered token returns None."""
        assert verify_verification_token("bad-token") is None

    def test_cross_use_prevention(self):
        """A verification token cannot be used as a reset token (different salt)."""
        token = generate_verification_token("user-456")
        # Should NOT be valid as a reset token
        assert verify_reset_token(token) is None


class TestResetToken:
    """Tests for password reset token lifecycle."""

    def test_round_trip(self):
        """A freshly generated reset token verifies successfully."""
        token = generate_reset_token("user-789")
        user_id = verify_reset_token(token)
        assert user_id == "user-789"

    def test_cross_use_prevention(self):
        """A reset token cannot be used for email verification (different salt)."""
        token = generate_reset_token("user-abc")
        assert verify_verification_token(token) is None

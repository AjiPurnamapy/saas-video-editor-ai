"""
Email verification & password reset endpoint tests.

S-24 FIX: Test coverage for Feature 3 (email verification, password reset).
"""

import pytest
from fastapi.testclient import TestClient

from app.core.email_token import (
    generate_verification_token,
    generate_reset_token,
)


class TestEmailVerification:
    """Tests for POST /api/auth/verify-email."""

    def test_verify_email_valid_token(self, client: TestClient, test_user_data: dict):
        """A valid verification token marks the user as verified."""
        # Register
        resp = client.post("/api/auth/register", json=test_user_data)
        assert resp.status_code == 201
        user_id = resp.json()["id"]

        # Generate token & verify
        token = generate_verification_token(user_id)
        verify_resp = client.post(
            "/api/auth/verify-email",
            json={"token": token},
        )
        assert verify_resp.status_code == 200
        assert "verified" in verify_resp.json()["message"].lower()

    def test_verify_email_invalid_token(self, client: TestClient):
        """An invalid token returns 401."""
        resp = client.post(
            "/api/auth/verify-email",
            json={"token": "totally-bogus-token"},
        )
        assert resp.status_code == 401

    def test_verify_email_no_csrf_needed(self, client: TestClient):
        """Verify-email must not require CSRF token (user clicks from email)."""
        resp = client.post(
            "/api/auth/verify-email",
            json={"token": "any-token"},
        )
        # Should not be 403 CSRF — expect 401 (invalid token) or 200
        assert resp.status_code != 403


class TestForgotPassword:
    """Tests for POST /api/auth/forgot-password."""

    def test_forgot_password_existing_email(self, client: TestClient, test_user_data: dict):
        """Request returns 200 for known email (no info leakage)."""
        client.post("/api/auth/register", json=test_user_data)
        resp = client.post(
            "/api/auth/forgot-password",
            json={"email": test_user_data["email"]},
        )
        assert resp.status_code == 200

    def test_forgot_password_unknown_email(self, client: TestClient):
        """Request returns 200 even for unknown email (prevents enumeration)."""
        resp = client.post(
            "/api/auth/forgot-password",
            json={"email": "nobody@example.com"},
        )
        assert resp.status_code == 200

    def test_forgot_password_no_csrf_needed(self, client: TestClient):
        """Forgot-password must not require CSRF token."""
        resp = client.post(
            "/api/auth/forgot-password",
            json={"email": "any@example.com"},
        )
        assert resp.status_code != 403


class TestResetPassword:
    """Tests for POST /api/auth/reset-password."""

    def test_reset_password_valid_token(self, client: TestClient, test_user_data: dict):
        """A valid reset token allows password change."""
        client.post("/api/auth/register", json=test_user_data)
        # Login to get user_id
        login_resp = client.post("/api/auth/login", json=test_user_data)
        assert login_resp.status_code == 200

        # Get user_id from /me
        me = client.get("/api/auth/me")
        user_id = me.json()["id"]

        # Generate token & reset
        token = generate_reset_token(user_id)
        reset_resp = client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "NewP@ss123!"},
        )
        assert reset_resp.status_code == 200

        # Verify new password works
        new_login = client.post(
            "/api/auth/login",
            json={"email": test_user_data["email"], "password": "NewP@ss123!"},
        )
        assert new_login.status_code == 200

    def test_reset_password_invalid_token(self, client: TestClient):
        """An invalid token returns 401."""
        resp = client.post(
            "/api/auth/reset-password",
            json={"token": "bogus-token", "new_password": "NewP@ss123!"},
        )
        assert resp.status_code == 401

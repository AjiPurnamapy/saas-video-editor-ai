"""
Authentication endpoint tests.

Tests for user registration, login, logout, and session management.
"""

import pytest
from fastapi.testclient import TestClient


class TestRegister:
    """Tests for POST /api/auth/register."""

    def test_register_success(self, client: TestClient):
        """Registering with valid credentials returns 201."""
        response = client.post("/api/auth/register", json={
            "email": "new@example.com",
            "password": "StrongPass1!",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@example.com"
        assert "id" in data
        assert "password" not in data
        assert "password_hash" not in data

    def test_register_duplicate_email(self, client: TestClient):
        """Registering with an existing email returns 409."""
        payload = {"email": "dup@example.com", "password": "StrongPass1!"}
        client.post("/api/auth/register", json=payload)
        response = client.post("/api/auth/register", json=payload)
        assert response.status_code == 409

    def test_register_short_password(self, client: TestClient):
        """Passwords shorter than 8 characters are rejected."""
        response = client.post("/api/auth/register", json={
            "email": "short@example.com",
            "password": "abc",
        })
        assert response.status_code == 422

    def test_register_invalid_email(self, client: TestClient):
        """Invalid email format is rejected."""
        response = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "StrongPass1!",
        })
        assert response.status_code == 422


class TestLogin:
    """Tests for POST /api/auth/login."""

    def test_login_success(self, client: TestClient, registered_user: dict):
        """Logging in with correct credentials returns 200 and sets cookie."""
        response = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert response.status_code == 200
        assert "session_id" in response.cookies

    def test_login_wrong_password(self, client: TestClient, registered_user: dict):
        """Wrong password returns 401."""
        response = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": "WrongPassword1!",
        })
        assert response.status_code == 401

    def test_login_nonexistent_email(self, client: TestClient):
        """Non-existent email returns 401."""
        response = client.post("/api/auth/login", json={
            "email": "nobody@example.com",
            "password": "StrongPass1!",
        })
        assert response.status_code == 401


class TestLogout:
    """Tests for POST /api/auth/logout."""

    def test_logout_clears_session(self, auth_client: TestClient):
        """Logging out clears the session cookie."""
        response = auth_client.post("/api/auth/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"

    def test_logout_unauthenticated(self, client: TestClient):
        """Logging out without a session returns 401."""
        response = client.post("/api/auth/logout")
        assert response.status_code == 401


class TestMe:
    """Tests for GET /api/auth/me."""

    def test_me_authenticated(self, auth_client: TestClient):
        """Authenticated user can retrieve their own info."""
        response = auth_client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "password" not in data

    def test_me_unauthenticated(self, client: TestClient):
        """Unauthenticated request returns 401."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

"""
Pytest fixtures and configuration.

Provides a test database (SQLite in-memory), test FastAPI client,
and helper fixtures for creating authenticated test sessions.
"""

import os
import uuid
import uuid as uuid_lib
from typing import Generator

import pytest

# SET BEFORE APP IMPORT
os.environ["TESTING"] = "1"
os.environ["APP_ENV"] = "testing"  # S-17: CSRF middleware uses app_env, not TESTING

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models.base import Base
# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

# S-15 FIX: Use in-memory SQLite (no leftover test.db files on disk)
# StaticPool ensures all threads share the same in-memory database
TEST_DATABASE_URL = "sqlite:///:memory:"

_test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=_test_engine,
)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Provide a clean database session for each test.

    Creates all tables before the test, drops them after.
    Each test gets a fully isolated database.
    """
    Base.metadata.create_all(bind=_test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=_test_engine)


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient with the test DB injected.

    Overrides the `get_db` dependency so routes use the test
    database session instead of the production PostgreSQL.
    """
    def _override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    
    # Disable rate limiting cleanly for testing
    from app.core.rate_limiter import limiter
    limiter.enabled = False
    
    with TestClient(app) as test_client:
        yield test_client
    
    limiter.enabled = True
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_user_data() -> dict:
    """Return valid user registration data."""
    return {
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "password": "SecurePass123!",
    }


@pytest.fixture
def registered_user(client: TestClient, test_user_data: dict) -> dict:
    """Register a user and return the response data."""
    response = client.post("/api/auth/register", json=test_user_data)
    assert response.status_code == 201
    return {**response.json(), "password": test_user_data["password"]}


@pytest.fixture
def auth_client(client: TestClient, test_user_data: dict) -> TestClient:
    """Provide an authenticated TestClient with a valid session cookie.

    Registers a user, logs in, and the client retains the
    session cookie for subsequent requests.

    S-20 FIX: Verifies auth actually works after login (not just 200).
    """
    # Register
    client.post("/api/auth/register", json=test_user_data)
    # Login (sets cookie on the client)
    response = client.post("/api/auth/login", json=test_user_data)
    assert response.status_code == 200, f"Login failed: {response.json()}"

    # Verify auth works — if session cookie is missing, this will fail
    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200, "Session cookie not working after login"

    return client

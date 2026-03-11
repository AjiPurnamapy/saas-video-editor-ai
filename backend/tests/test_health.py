"""
Health check and smoke tests.

Basic tests to verify the application starts and key endpoints respond.
"""

from fastapi.testclient import TestClient


class TestHealthCheck:
    """Tests for GET /health."""

    def test_health_returns_200(self, client: TestClient):
        """Health check endpoint returns status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert "version" in data
        assert "components" in data

    def test_health_has_component_status(self, client: TestClient):
        """Health check includes database and redis component status."""
        response = client.get("/health")
        data = response.json()
        components = data.get("components", {})
        assert "database" in components
        assert "redis" in components


class TestDocs:
    """Tests for API documentation endpoints."""

    def test_docs_accessible(self, client: TestClient):
        """Swagger UI endpoint is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_accessible(self, client: TestClient):
        """ReDoc endpoint is accessible."""
        response = client.get("/redoc")
        assert response.status_code == 200


class TestAppErrorHandler:
    """Tests that domain exceptions are properly handled."""

    def test_404_returns_json(self, auth_client: TestClient):
        """NotFoundError returns clean JSON with detail field."""
        response = auth_client.get("/api/videos/nonexistent-uuid")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_401_unauthenticated(self, client: TestClient):
        """Unauthenticated requests return clean 401 JSON."""
        response = client.get("/api/videos")
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

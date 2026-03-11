"""
Output endpoint tests.

Tests for listing and retrieving processed video outputs.
"""

import io

import pytest
from fastapi.testclient import TestClient


def _upload_video(client: TestClient) -> str:
    """Upload a fake video and return its ID."""
    response = client.post(
        "/api/videos/upload",
        files={"file": ("test.mp4", io.BytesIO(b"\x00" * 512), "video/mp4")},
    )
    assert response.status_code == 201
    return response.json()["id"]


class TestListOutputs:
    """Tests for GET /api/outputs?video_id=xxx."""

    def test_list_outputs_empty(self, auth_client: TestClient):
        """Listing outputs for a video with none returns empty list."""
        video_id = _upload_video(auth_client)
        response = auth_client.get(f"/api/outputs?video_id={video_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["outputs"] == []
        assert data["total"] == 0

    def test_list_outputs_video_not_found(self, auth_client: TestClient):
        """Listing outputs for a non-existent video returns 404."""
        response = auth_client.get("/api/outputs?video_id=nonexistent-id")
        assert response.status_code == 404

    def test_list_outputs_unauthenticated(self, client: TestClient):
        """Listing outputs without auth returns 401."""
        response = client.get("/api/outputs?video_id=some-id")
        assert response.status_code == 401

    def test_list_outputs_missing_video_id(self, auth_client: TestClient):
        """Listing outputs without video_id query param returns 422."""
        response = auth_client.get("/api/outputs")
        assert response.status_code == 422


class TestGetOutput:
    """Tests for GET /api/outputs/{output_id}."""

    def test_get_output_not_found(self, auth_client: TestClient):
        """Getting a non-existent output returns 404."""
        response = auth_client.get("/api/outputs/nonexistent-id")
        assert response.status_code == 404

    def test_get_output_unauthenticated(self, client: TestClient):
        """Getting an output without auth returns 401."""
        response = client.get("/api/outputs/some-id")
        assert response.status_code == 401

"""
Job endpoint tests.

Tests for job creation and status retrieval, including ownership checks.
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


class TestStartJob:
    """Tests for POST /api/jobs/start."""

    def test_start_job_success(self, auth_client: TestClient):
        """Starting a job for an owned video returns 201."""
        video_id = _upload_video(auth_client)
        response = auth_client.post("/api/jobs/start", json={"video_id": video_id})
        assert response.status_code == 201
        data = response.json()
        assert data["video_id"] == video_id
        assert data["status"] == "queued"

    def test_start_job_duplicate(self, auth_client: TestClient):
        """Starting a second job on the same video returns 409."""
        video_id = _upload_video(auth_client)
        auth_client.post("/api/jobs/start", json={"video_id": video_id})
        response = auth_client.post("/api/jobs/start", json={"video_id": video_id})
        assert response.status_code == 409

    def test_start_job_nonexistent_video(self, auth_client: TestClient):
        """Starting a job for a non-existent video returns 404."""
        response = auth_client.post(
            "/api/jobs/start", json={"video_id": "nonexistent-id"}
        )
        assert response.status_code == 404

    def test_start_job_unauthenticated(self, client: TestClient):
        """Starting a job without auth returns 401."""
        response = client.post(
            "/api/jobs/start", json={"video_id": "any-id"}
        )
        assert response.status_code == 401


class TestGetJob:
    """Tests for GET /api/jobs/{job_id}."""

    def test_get_job_success(self, auth_client: TestClient):
        """Retrieving a job the user owns returns 200."""
        video_id = _upload_video(auth_client)
        start = auth_client.post("/api/jobs/start", json={"video_id": video_id})
        job_id = start.json()["id"]

        response = auth_client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id
        assert data["status"] == "queued"
        assert data["progress"] == 0

    def test_get_job_not_found(self, auth_client: TestClient):
        """Requesting a non-existent job returns 404."""
        response = auth_client.get("/api/jobs/nonexistent-id")
        assert response.status_code == 404

    def test_get_job_unauthenticated(self, client: TestClient):
        """Requesting a job without auth returns 401."""
        response = client.get("/api/jobs/some-id")
        assert response.status_code == 401

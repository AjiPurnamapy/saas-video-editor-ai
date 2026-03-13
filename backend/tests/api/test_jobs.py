"""
Job endpoint tests.

Tests for job creation and status retrieval, including ownership checks.
"""

import io
import uuid

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.models.enums import JobStatus, VideoStatus
from app.models.job import Job
from app.models.video import Video
from app.models.user import User


def _get_user_id(db_session) -> str:
    """Get the first registered user's ID from the test database."""
    user = db_session.query(User).first()
    return str(user.id)


class TestStartJob:
    """Tests for POST /api/jobs/start."""

    def test_start_job_success(self, auth_client: TestClient, db_session):
        """Starting a job for an owned video returns 201."""
        user_id = _get_user_id(db_session)
        video_id = str(uuid.uuid4())
        video = Video(id=video_id, user_id=user_id, raw_video_path="/tmp/test.mp4", status=VideoStatus.UPLOADED)
        db_session.add(video)
        db_session.commit()

        response = auth_client.post("/api/jobs/start", json={"video_id": video_id})
        assert response.status_code == 201
        data = response.json()
        assert data["video_id"] == video_id
        assert data["status"] == "queued"

    def test_start_job_duplicate(self, auth_client: TestClient, db_session):
        """Starting a second job on the same video returns 409."""
        user_id = _get_user_id(db_session)
        video_id = str(uuid.uuid4())
        video = Video(id=video_id, user_id=user_id, raw_video_path="/tmp/test.mp4", status=VideoStatus.UPLOADED)
        db_session.add(video)
        db_session.commit()

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

    def test_get_job_success(self, auth_client: TestClient, db_session):
        """Retrieving a job the user owns returns 200."""
        user_id = _get_user_id(db_session)
        video_id = str(uuid.uuid4())
        video = Video(id=video_id, user_id=user_id, raw_video_path="/tmp/test.mp4", status=VideoStatus.UPLOADED)
        db_session.add(video)
        db_session.commit()

        start = auth_client.post("/api/jobs/start", json={"video_id": video_id})
        assert start.status_code == 201
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


class TestCancelJob:
    """Tests for POST /api/jobs/{job_id}/cancel."""

    def test_cancel_job_success(self, auth_client: TestClient, db_session):
        """User can cancel an active job."""
        user_id = _get_user_id(db_session)
        video_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())

        video = Video(id=video_id, user_id=user_id, raw_video_path="/f", status=VideoStatus.PROCESSING)
        job = Job(id=job_id, video_id=video.id, status=JobStatus.PROCESSING, progress=10)
        db_session.add(video)
        db_session.add(job)
        db_session.commit()

        response = auth_client.post(f"/api/jobs/{job_id}/cancel")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_cancel_job_wrong_user(self, client: TestClient, test_user_data: dict, db_session):
        """Cannot cancel a job belonging to another user (returns 403 or 404)."""
        # Register and login user A
        client.post("/api/auth/register", json=test_user_data)
        client.post("/api/auth/login", json=test_user_data)

        # Insert Job manually for User B (different user_id)
        other_user_id = str(uuid.uuid4())
        video = Video(id=str(uuid.uuid4()), user_id=other_user_id, raw_video_path="/f", status=VideoStatus.PROCESSING)
        job_id = str(uuid.uuid4())
        job = Job(id=job_id, video_id=video.id, status=JobStatus.PROCESSING, progress=10)
        db_session.add(video)
        db_session.add(job)
        db_session.commit()

        # User A tries to cancel User B's job - should fail
        response = client.post(f"/api/jobs/{job_id}/cancel")
        assert response.status_code in [403, 404]

    def test_cancel_already_completed(self, auth_client: TestClient, db_session):
        """Cancelling a completed job returns error."""
        user_id = _get_user_id(db_session)
        job_id = str(uuid.uuid4())

        video = Video(id=str(uuid.uuid4()), user_id=user_id, raw_video_path="/f", status=VideoStatus.COMPLETED)
        job = Job(id=job_id, video_id=video.id, status=JobStatus.COMPLETED, progress=100)
        db_session.add(video)
        db_session.add(job)
        db_session.commit()

        response = auth_client.post(f"/api/jobs/{job_id}/cancel")
        assert response.status_code in [400, 409]

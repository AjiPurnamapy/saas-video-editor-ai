"""
Video endpoint tests.

Tests for video upload, listing, retrieval, and deletion.
"""

import io

import pytest
from fastapi.testclient import TestClient


def _make_fake_video(size_bytes: int = 1024, filename: str = "test.mp4") -> tuple:
    """Create a fake video file for upload testing.

    Returns:
        A tuple of (filename, file-like object, content_type).
    """
    content = b"\x00" * size_bytes
    return (filename, io.BytesIO(content), "video/mp4")


class TestUpload:
    """Tests for POST /api/videos/upload."""

    def test_upload_success(self, auth_client: TestClient):
        """Uploading a valid video returns 201."""
        file = _make_fake_video()
        response = auth_client.post(
            "/api/videos/upload",
            files={"file": file},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "uploaded"
        assert "id" in data
        assert data["original_filename"] == "test.mp4"

    def test_upload_invalid_type(self, auth_client: TestClient):
        """Uploading a non-video file returns 400."""
        response = auth_client.post(
            "/api/videos/upload",
            files={"file": ("doc.pdf", io.BytesIO(b"fake"), "application/pdf")},
        )
        assert response.status_code == 400

    def test_upload_unauthenticated(self, client: TestClient):
        """Uploading without auth returns 401."""
        file = _make_fake_video()
        response = client.post(
            "/api/videos/upload",
            files={"file": file},
        )
        assert response.status_code == 401

    def test_upload_path_traversal_filename(self, auth_client: TestClient):
        """Filenames with path traversal are sanitized."""
        file = ("../../etc/passwd", io.BytesIO(b"\x00" * 100), "video/mp4")
        response = auth_client.post(
            "/api/videos/upload",
            files={"file": file},
        )
        # Should succeed — filename is sanitized, not rejected
        assert response.status_code == 201
        data = response.json()
        # Filename should have been sanitized (no directory components)
        assert "/" not in data["original_filename"]
        assert ".." not in data["original_filename"]


class TestListVideos:
    """Tests for GET /api/videos."""

    def test_list_empty(self, auth_client: TestClient):
        """Listing with no videos returns empty list."""
        response = auth_client.get("/api/videos")
        assert response.status_code == 200
        data = response.json()
        assert data["videos"] == []
        assert data["total"] == 0

    def test_list_after_upload(self, auth_client: TestClient):
        """Uploaded videos appear in the list."""
        auth_client.post(
            "/api/videos/upload",
            files={"file": _make_fake_video()},
        )
        response = auth_client.get("/api/videos")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["videos"]) == 1

    def test_list_no_internal_paths(self, auth_client: TestClient):
        """Video list does not expose internal file paths."""
        auth_client.post(
            "/api/videos/upload",
            files={"file": _make_fake_video()},
        )
        response = auth_client.get("/api/videos")
        video = response.json()["videos"][0]
        assert "raw_video_path" not in video


class TestGetVideo:
    """Tests for GET /api/videos/{video_id}."""

    def test_get_video_success(self, auth_client: TestClient):
        """Retrieving an existing video returns its details."""
        upload = auth_client.post(
            "/api/videos/upload",
            files={"file": _make_fake_video()},
        )
        video_id = upload.json()["id"]
        response = auth_client.get(f"/api/videos/{video_id}")
        assert response.status_code == 200
        assert response.json()["id"] == video_id

    def test_get_video_not_found(self, auth_client: TestClient):
        """Requesting a non-existent video returns 404."""
        response = auth_client.get("/api/videos/nonexistent-id")
        assert response.status_code == 404


class TestDeleteVideo:
    """Tests for DELETE /api/videos/{video_id}."""

    def test_delete_video_success(self, auth_client: TestClient):
        """Deleting a video returns 200 and removes it."""
        upload = auth_client.post(
            "/api/videos/upload",
            files={"file": _make_fake_video()},
        )
        video_id = upload.json()["id"]
        response = auth_client.delete(f"/api/videos/{video_id}")
        assert response.status_code == 200

        # Verify it's gone
        get_response = auth_client.get(f"/api/videos/{video_id}")
        assert get_response.status_code == 404

    def test_delete_video_not_found(self, auth_client: TestClient):
        """Deleting a non-existent video returns 404."""
        response = auth_client.delete("/api/videos/nonexistent-id")
        assert response.status_code == 404

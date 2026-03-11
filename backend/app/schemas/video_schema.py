"""
Video Pydantic schemas.

Defines request/response models for video-related endpoints.

SECURITY: raw_video_path is intentionally excluded from all public
response schemas to avoid leaking internal server paths. Only safe
metadata is exposed to API consumers.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class VideoResponse(BaseModel):
    """Video information returned by the API.

    Note: raw_video_path is NOT included — internal file paths
    must never be exposed to clients.
    """

    id: str
    user_id: str
    original_filename: Optional[str] = None
    duration: Optional[float] = None
    file_size_bytes: Optional[int] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    """Paginated list of videos."""

    videos: List[VideoResponse]
    total: int


class VideoUploadResponse(BaseModel):
    """Response after a successful video upload."""

    id: str
    original_filename: str
    file_size_bytes: int
    status: str
    message: str = "Video uploaded successfully"

    model_config = {"from_attributes": True}

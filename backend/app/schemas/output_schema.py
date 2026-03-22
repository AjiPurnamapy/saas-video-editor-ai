"""
Output Pydantic schemas.

Defines response models for processed video output endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class OutputResponse(BaseModel):
    """Processed video output information returned by the API.

    S-16 FIX: file_path (internal filesystem path) is NOT exposed.
    Use the /download-url endpoint to get a signed URL instead.
    """

    id: str
    video_id: str
    resolution: Optional[str] = None
    duration: Optional[float] = None
    file_size_bytes: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OutputListResponse(BaseModel):
    """List of outputs for a video."""

    outputs: List[OutputResponse]
    total: int


class DownloadUrlResponse(BaseModel):
    """Signed download URL response."""

    download_url: str
    expires_in: int  # seconds until expiry

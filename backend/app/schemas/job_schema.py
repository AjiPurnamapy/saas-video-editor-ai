"""
Job Pydantic schemas.

Defines request/response models for job-related endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class JobStartRequest(BaseModel):
    """Request body to start a video processing job."""

    video_id: str = Field(
        ...,
        description="ID of the video to process",
    )


class JobResponse(BaseModel):
    """Job information returned by the API."""

    id: str
    video_id: str
    status: str
    progress: int
    task_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobStartResponse(BaseModel):
    """Response after starting a processing job."""

    id: str
    video_id: str
    status: str
    task_id: Optional[str] = None
    message: str = "Processing job started"


class JobCancelResponse(BaseModel):
    """Response after cancelling a processing job."""

    id: str
    video_id: str
    status: str
    message: str = "Processing job cancelled"

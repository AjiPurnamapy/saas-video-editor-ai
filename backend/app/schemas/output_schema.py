"""
Output Pydantic schemas.

Defines response models for processed video output endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class OutputResponse(BaseModel):
    """Processed video output information returned by the API."""

    id: str
    video_id: str
    file_url: str
    resolution: Optional[str] = None
    duration: Optional[float] = None
    file_size_bytes: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OutputListResponse(BaseModel):
    """List of outputs for a video."""

    outputs: List[OutputResponse]
    total: int

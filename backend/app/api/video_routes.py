"""
Video API routes.

Endpoints for uploading, listing, retrieving, and deleting videos.
All endpoints require authentication.

SECURITY (C-02 FIX):
- All endpoints are rate-limited to prevent resource exhaustion
- Upload: 10/min, 50/hour | List/Get: 60/min | Delete: 20/min
"""

from fastapi import APIRouter, Depends, Request, Response, UploadFile, File, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.rate_limiter import limiter
from app.database import get_db
from app.models.user import User
from app.schemas.user_schema import MessageResponse
from app.schemas.video_schema import (
    VideoListResponse,
    VideoResponse,
    VideoUploadResponse,
)
from app.services.video_service import VideoService

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a video",
)
@limiter.limit("10/minute")
@limiter.limit("50/hour")
async def upload_video(
    request: Request,
    response: Response,
    file: UploadFile = File(..., description="Video file to upload"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VideoUploadResponse:
    """Upload a raw video file for processing.

    Accepts common video formats (MP4, MOV, AVI, MKV, WebM, MPEG).
    Maximum file size is configurable via MAX_UPLOAD_SIZE_MB.
    Rate limited to 10 uploads per minute and 50 per hour.

    Args:
        request: FastAPI request (required by slowapi limiter).
        file: The uploaded video file.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Upload confirmation with the video ID and metadata.
    """
    service = VideoService(db)
    video = await service.upload_video(file, current_user.id)
    return VideoUploadResponse(
        id=video.id,
        original_filename=video.original_filename or "",
        file_size_bytes=video.file_size_bytes or 0,
        status=video.status,
    )


@router.get(
    "",
    response_model=VideoListResponse,
    summary="List user videos",
)
@limiter.limit("60/minute")
def list_videos(
    request: Request,
    response: Response,
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Records per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VideoListResponse:
    """List all videos uploaded by the current user.

    Supports pagination via skip/limit parameters.
    Rate limited to 60 requests per minute.

    Args:
        request: FastAPI request (required by slowapi limiter).
        skip: Number of records to skip.
        limit: Maximum records to return (1-100).
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Paginated list of videos with total count.
    """
    service = VideoService(db)
    videos, total = service.list_videos(current_user.id, skip, limit)
    return VideoListResponse(
        videos=[VideoResponse.model_validate(v) for v in videos],
        total=total,
    )


@router.get(
    "/{video_id}",
    response_model=VideoResponse,
    summary="Get video details",
)
@limiter.limit("60/minute")
def get_video(
    request: Request,
    response: Response,
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VideoResponse:
    """Retrieve details of a specific video.

    Only returns videos owned by the authenticated user.
    Rate limited to 60 requests per minute.

    Args:
        request: FastAPI request (required by slowapi limiter).
        video_id: The video UUID.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The video's full details.
    """
    service = VideoService(db)
    video = service.get_video(video_id, current_user.id)
    return VideoResponse.model_validate(video)


@router.delete(
    "/{video_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a video",
)
@limiter.limit("20/minute")
def delete_video(
    request: Request,
    response: Response,
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a video and its stored file.

    Only allows deletion of videos owned by the authenticated user.
    Also removes the associated file from storage.
    Rate limited to 20 requests per minute.

    Args:
        request: FastAPI request (required by slowapi limiter).
        video_id: The video UUID.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        204 No Content on success.
    """
    service = VideoService(db)
    service.delete_video(video_id, current_user.id)

"""
Output API routes.

Endpoints for listing and retrieving processed video outputs,
and generating signed download URLs.

All endpoints require authentication and enforce ownership,
except the download endpoint which uses a signed token for auth.
"""

import mimetypes
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.rate_limiter import limiter
from app.core.signed_url import (
    generate_download_token,
    verify_download_token,
    DOWNLOAD_TOKEN_MAX_AGE,
)
from app.database import get_db
from app.models.user import User
from app.schemas.output_schema import (
    DownloadUrlResponse,
    OutputListResponse,
    OutputResponse,
)
from app.services.output_service import OutputService

router = APIRouter(prefix="/outputs", tags=["Outputs"])


@router.get(
    "",
    response_model=OutputListResponse,
    summary="List outputs for a video",
)
def list_outputs(
    video_id: str = Query(..., description="Video ID to list outputs for"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutputListResponse:
    """List all processed outputs for a specific video.

    Only returns outputs for videos owned by the authenticated user.

    Args:
        video_id: The video UUID to list outputs for.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        List of outputs with total count.
    """
    service = OutputService(db)
    outputs, total = service.list_outputs(video_id, current_user.id)
    return OutputListResponse(
        outputs=[OutputResponse.model_validate(o) for o in outputs],
        total=total,
    )


@router.get(
    "/{output_id}",
    response_model=OutputResponse,
    summary="Get output details",
)
def get_output(
    output_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutputResponse:
    """Retrieve details of a specific processed output.

    Only returns outputs for videos owned by the authenticated user.

    Args:
        output_id: The output UUID.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The output's full details.
    """
    service = OutputService(db)
    output = service.get_output(output_id, current_user.id)
    return OutputResponse.model_validate(output)


@router.get(
    "/{output_id}/download-url",
    response_model=DownloadUrlResponse,
    summary="Generate signed download URL",
)
@limiter.limit("30/minute")
def get_download_url(
    request: Request,
    output_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DownloadUrlResponse:
    """Generate a time-limited signed URL for downloading an output.

    The signed URL is valid for 1 hour and can be opened directly
    in a browser or used by the frontend to trigger a download.
    No session cookie is needed to use the download URL.

    Rate limited to 30 per minute.

    Args:
        request: FastAPI request (for building URL + rate limiting).
        output_id: The output UUID to generate a download URL for.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The signed download URL and its expiry time.
    """
    # Verify ownership
    service = OutputService(db)
    service.get_output(output_id, current_user.id)  # raises NotFoundError

    # Generate signed token
    token = generate_download_token(output_id, current_user.id)

    # Build full download URL
    base_url = str(request.base_url).rstrip("/")
    download_url = f"{base_url}/api/outputs/download/{token}"

    return DownloadUrlResponse(
        download_url=download_url,
        expires_in=DOWNLOAD_TOKEN_MAX_AGE,
    )


@router.get(
    "/download/{token}",
    summary="Download output via signed token",
    responses={
        200: {"content": {"video/mp4": {}}, "description": "Video file"},
        400: {"description": "Invalid or expired token"},
        404: {"description": "Output file not found"},
    },
)
def download_output(
    token: str,
    db: Session = Depends(get_db),
):
    """Download an output video using a signed token.

    This endpoint does NOT require session authentication — the
    signed token IS the authorization. This allows:
    - Opening download links directly in new browser tabs
    - Sharing temporary download links

    The token expires after 1 hour.

    Args:
        token: The signed download token from /download-url.
        db: Database session (injected).

    Returns:
        The video file as a streaming download.

    Raises:
        400: If the token is invalid or expired.
        404: If the output or file is not found.
    """
    # Verify token
    payload = verify_download_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired download token",
        )

    output_id = payload.get("output_id")
    user_id = payload.get("user_id")

    if not output_id or not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed download token",
        )

    # Verify output still exists and belongs to the user
    service = OutputService(db)
    try:
        output = service.get_output(output_id, user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output not found",
        )

    # Verify file exists on disk
    file_path = output.file_url
    if not file_path or not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output file not found on server",
        )

    # S-07 FIX: Validate file extension before serving
    ALLOWED_SERVE_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext not in ALLOWED_SERVE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output file not found on server",
        )

    # Dynamic MIME type detection
    media_type, _ = mimetypes.guess_type(file_path)
    media_type = media_type or "video/mp4"

    # Determine filename for download
    original_filename = f"output_{output_id[:8]}{file_ext}"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=original_filename,
        headers={
            "Content-Disposition": f'attachment; filename="{original_filename}"',
        },
    )

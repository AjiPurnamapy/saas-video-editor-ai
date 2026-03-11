"""
Output API routes.

Endpoints for listing and retrieving processed video outputs.
All endpoints require authentication and enforce ownership.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.output_schema import OutputListResponse, OutputResponse
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

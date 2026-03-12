"""
Job API routes.

Endpoints for starting and monitoring video processing jobs.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.job_schema import JobResponse, JobStartRequest, JobStartResponse
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "/start",
    response_model=JobStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a processing job",
)
def start_job(
    data: JobStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobStartResponse:
    """Start a new video processing job.

    Creates a job record and dispatches the processing task
    to the Celery worker queue. Returns immediately without
    waiting for processing to complete.

    Only one active job (queued or processing) is allowed per video.

    Args:
        data: Job start request with the video ID.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Job creation confirmation with the job ID, task ID, and initial status.
    """
    service = JobService(db)
    job = service.create_job(data.video_id, current_user.id)

    # Ensure root project directory is in sys.path so we can import 'workers'
    import sys
    import os
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    # Dispatch to Celery worker
    from workers.tasks.video_tasks import process_video
    result = process_video.delay(job.id)
    service.set_task_id(job.id, result.id)

    return JobStartResponse(
        id=job.id,
        video_id=job.video_id,
        status=job.status,
        task_id=result.id,
    )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job status",
)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResponse:
    """Retrieve the current status of a processing job.

    Returns the job's status, progress percentage, and any
    error information.

    Args:
        job_id: The job UUID.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The job's current state and progress.
    """
    service = JobService(db)
    job = service.get_job(job_id, current_user.id)
    return JobResponse.model_validate(job)

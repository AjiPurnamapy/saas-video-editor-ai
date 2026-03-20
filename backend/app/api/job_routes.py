"""
Job API routes.

Endpoints for starting, monitoring, and cancelling video processing jobs.

SECURITY (C-02 FIX):
- All endpoints are rate-limited to prevent queue flooding
- Start: 20/min, 100/hour | Get: 60/min | Cancel: 20/min
"""

import os
import sys

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.rate_limiter import limiter
from app.database import get_db
from app.models.user import User

# H2 Fix: Centralize sys.path setup at module level (not per-request)
# This ensures 'workers' package is importable when job_routes is loaded.
_project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from app.schemas.job_schema import (
    JobCancelResponse,
    JobResponse,
    JobStartRequest,
    JobStartResponse,
)
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "/start",
    response_model=JobStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a processing job",
)
@limiter.limit("20/minute")
@limiter.limit("100/hour")
def start_job(
    request: Request,
    data: JobStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobStartResponse:
    """Start a new video processing job.

    Creates a job record and dispatches the processing task
    to the Celery worker queue. Returns immediately without
    waiting for processing to complete.

    Only one active job (queued or processing) is allowed per video.
    Rate limited to 20 starts per minute and 100 per hour.

    Args:
        request: FastAPI request (required by slowapi limiter).
        data: Job start request with the video ID.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Job creation confirmation with the job ID, task ID, and initial status.
    """
    service = JobService(db)
    job = service.create_job(data.video_id, current_user.id)

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
@limiter.limit("60/minute")
def get_job(
    request: Request,
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResponse:
    """Retrieve the current status of a processing job.

    Returns the job's status, progress percentage, and any
    error information.
    Rate limited to 60 requests per minute.

    Args:
        request: FastAPI request (required by slowapi limiter).
        job_id: The job UUID.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        The job's current state and progress.
    """
    service = JobService(db)
    job = service.get_job(job_id, current_user.id)
    return JobResponse.model_validate(job)


@router.post(
    "/{job_id}/cancel",
    response_model=JobCancelResponse,
    summary="Cancel a processing job",
)
@limiter.limit("20/minute")
def cancel_job(
    request: Request,
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobCancelResponse:
    """Cancel a queued or in-progress video processing job.

    Sets the job status to 'cancelled'. If the worker is currently
    processing this job, it will stop at the next pipeline checkpoint
    and clean up temporary files.
    Rate limited to 20 requests per minute.

    Args:
        request: FastAPI request (required by slowapi limiter).
        job_id: The job UUID to cancel.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        Cancellation confirmation with the updated job status.
    """
    service = JobService(db)
    job = service.cancel_job(job_id, current_user.id)
    return JobCancelResponse(
        id=job.id,
        video_id=job.video_id,
        status=job.status,
    )

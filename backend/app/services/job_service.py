"""
Job service.

Business logic for creating and managing video processing jobs.

SECURITY: All job retrieval methods enforce user ownership checks
to prevent unauthorized access to other users' job data.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.enums import JobStatus, VideoStatus
from app.models.job import Job
from app.models.video import Video

logger = logging.getLogger(__name__)


class JobService:
    """Encapsulates job management business logic."""

    def __init__(self, db: Session) -> None:
        """Initialize JobService with a database session.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db

    def create_job(self, video_id: str, user_id: str) -> Job:
        """Create a new processing job for a video.

        Validates that the video belongs to the user and is in a
        processable state before creating the job record.

        Args:
            video_id: The video UUID to process.
            user_id: The requesting user's UUID.

        Returns:
            The created Job model.

        Raises:
            NotFoundError: If the video is not found.
            ConflictError: If the video already has an active job.
        """
        # Verify video ownership
        video = (
            self.db.query(Video)
            .filter(Video.id == video_id, Video.user_id == user_id)
            .first()
        )
        if not video:
            raise NotFoundError("Video not found")

        # Check for existing active job (uses SELECT FOR UPDATE to prevent
        # race conditions where two requests pass this check simultaneously)
        active_job = (
            self.db.query(Job)
            .filter(
                Job.video_id == video_id,
                Job.status.in_([JobStatus.QUEUED, JobStatus.PROCESSING]),
            )
            .with_for_update()
            .first()
        )
        if active_job:
            raise ConflictError("Video already has an active processing job")

        # Create job
        job = Job(
            video_id=video_id,
            status=JobStatus.QUEUED,
            progress=0,
        )
        self.db.add(job)

        # Update video status
        video.status = VideoStatus.PROCESSING
        self.db.commit()
        self.db.refresh(job)

        logger.info("Job created: id=%s video=%s user=%s", job.id, video_id, user_id)
        return job

    def get_job(self, job_id: str, user_id: str) -> Job:
        """Retrieve a job by ID with ownership verification.

        Joins through the Video table to verify the requesting user
        owns the video associated with this job.

        Args:
            job_id: The job UUID.
            user_id: The requesting user's UUID.

        Returns:
            The Job model.

        Raises:
            NotFoundError: If the job is not found or does not
                           belong to the authenticated user.
        """
        job = (
            self.db.query(Job)
            .join(Video, Job.video_id == Video.id)
            .filter(Job.id == job_id, Video.user_id == user_id)
            .first()
        )
        if not job:
            raise NotFoundError("Job not found")
        return job

    def update_job_status(
        self,
        job_id: str,
        status_value: str,
        progress: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> Job:
        """Update the status and progress of a job.

        This is called by Celery workers as they process video tasks.
        This internal method does NOT enforce user ownership — it is
        only called by trusted worker processes.

        Args:
            job_id: The job UUID.
            status_value: New status (queued, processing, completed, failed).
            progress: Progress percentage (0-100).
            error_message: Error details if the job failed.

        Returns:
            The updated Job model.

        Raises:
            NotFoundError: If the job is not found.
        """
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise NotFoundError("Job not found")

        job.status = status_value

        if progress is not None:
            job.progress = progress
        if error_message is not None:
            job.error_message = error_message

        self.db.commit()
        self.db.refresh(job)

        logger.info(
            "Job status updated: id=%s status=%s progress=%s",
            job_id, status_value, progress,
        )
        return job

    def set_task_id(self, job_id: str, task_id: str) -> None:
        """Store the Celery task ID on a job record.

        Called immediately after dispatching the task to the Celery queue
        so the job can be traced back to its async worker.

        Args:
            job_id: The job UUID.
            task_id: The Celery task ID returned by .delay() or .apply_async().
        """
        from app.models.job import Job

        job = self.db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.task_id = task_id
            self.db.commit()
            logger.info("Task ID saved: job=%s task=%s", job_id, task_id)

    def cancel_job(self, job_id: str, user_id: str) -> Job:
        """Cancel a queued or processing job.

        Sets the job status to CANCELLED and revokes the Celery task.
        The worker checks for cancellation between each pipeline step.

        Args:
            job_id: The job UUID.
            user_id: The requesting user's UUID (for ownership check).

        Returns:
            The updated Job model.

        Raises:
            NotFoundError: If the job is not found or unauthorized.
            ConflictError: If the job is not in a cancellable state.
        """
        # Ownership check via join
        job = (
            self.db.query(Job)
            .join(Video, Job.video_id == Video.id)
            .filter(Job.id == job_id, Video.user_id == user_id)
            .first()
        )
        if not job:
            raise NotFoundError("Job not found")

        # Only queued or processing jobs can be cancelled
        if job.status not in (JobStatus.QUEUED, JobStatus.PROCESSING):
            raise ConflictError(
                f"Cannot cancel job with status '{job.status}'. "
                f"Only queued or processing jobs can be cancelled."
            )

        # Update status
        job.status = JobStatus.CANCELLED
        job.error_message = "Cancelled by user"
        self.db.commit()
        self.db.refresh(job)

        # Revoke the Celery task (signal worker to stop)
        if job.task_id:
            try:
                from app.core.celery_client import revoke_task
                revoke_task(job.task_id)
            except Exception as exc:
                # Non-critical: worker will check DB status anyway
                logger.warning("Failed to revoke task %s: %s", job.task_id, exc)

        logger.info("Job cancelled: id=%s user=%s", job_id, user_id)
        return job

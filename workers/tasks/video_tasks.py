"""
Video processing Celery task.

Orchestrates the video processing pipeline: audio extraction,
silence detection, clip cutting, resizing, and subtitle burning.

This task is the bridge between the Celery worker and the existing
service/utils layers. It does NOT contain business logic — it only
calls existing functions from app.utils.ffmpeg_utils and updates
job status via app.services.job_service.

DESIGN PRINCIPLES:
- Idempotent: Re-running with the same job_id is safe (checks status)
- Retriable: Uses exponential backoff (10s, 20s, 40s)
- Crash-safe: task_acks_late ensures re-delivery on worker crash
- Clean: Temporary files are cleaned up on success or failure
"""

import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from typing import Optional

from celery import Task
from celery.utils.log import get_task_logger

from workers.celery_app import celery_app, ffmpeg_semaphore

# Use Celery's task logger for structured worker output
logger = get_task_logger(__name__)


# --- Worker-dedicated Database Pool (R3) ---
# Workers use their own connection pool, separate from the API's pool.
# This prevents connection exhaustion when both API and workers are
# accessing the database simultaneously under heavy load.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

_worker_settings = get_settings()
_worker_engine = create_engine(
    _worker_settings.database_url,
    pool_size=3,        # Small pool — workers do sequential DB ops
    max_overflow=5,     # Burst up to 8 total connections
    pool_pre_ping=True, # Verify connection before use
    pool_recycle=1800,  # Recycle connections every 30 min
)
WorkerSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=_worker_engine,
)

# Minimum free disk space required before starting a job (bytes)
MIN_FREE_DISK_BYTES = 2 * 1024 ** 3  # 2 GB


def _get_db_session():
    """Create a standalone database session for the worker.

    Uses the worker-dedicated connection pool (separate from API)
    to prevent connection exhaustion under concurrent load.
    """
    return WorkerSessionLocal()


class VideoProcessingTask(Task):
    """Custom Task base class with automatic DB session cleanup.

    Ensures the database session is always closed, even if the
    task raises an exception.

    NOTE: _db is stored per-request (not as a class attribute)
    because Celery Task classes are singletons — the same instance
    is reused for every task execution. Using a class attribute
    would cause session cross-contamination under concurrent pools.
    """

    @property
    def db_session(self):
        """Get the current request's DB session (if any)."""
        return getattr(self, '_db', None)

    @db_session.setter
    def db_session(self, value):
        self._db = value

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Called after the task returns (success or failure)."""
        db = getattr(self, '_db', None)
        if db is not None:
            db.close()
            self._db = None


@celery_app.task(
    bind=True,
    base=VideoProcessingTask,
    name="workers.tasks.video_tasks.process_video",
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
    time_limit=1800,        # Hard kill after 30 minutes
    soft_time_limit=1500,   # Raise SoftTimeLimitExceeded after 25 min
    retry_backoff=True,     # Exponential backoff: 10s, 20s, 40s, ...
    retry_jitter=True,      # Add random jitter to prevent thundering herd
)
def process_video(self: VideoProcessingTask, job_id: str) -> dict:
    """Process a video through the full editing pipeline.

    Pipeline steps:
    1. Extract audio from video (for Whisper transcription)
    2. Detect silence segments in audio
    3. Cut video into clips (removing silent parts)
    4. Resize clips to 9:16 vertical format
    5. Save output records to database

    Args:
        job_id: UUID of the Job record to process.

    Returns:
        A dict with job_id, status, and output count.

    Retries:
        Up to 3 times with exponential backoff (10s, 20s, 40s)
        on FFmpeg errors and transient failures.
    """
    from app.services.job_service import JobService
    from app.models.enums import JobStatus, VideoStatus
    from app.models.video import Video
    from app.models.output import Output

    logger.info("Task started: job_id=%s attempt=%d", job_id, self.request.retries + 1)

    # Get fresh DB session
    db = _get_db_session()
    self._db = db
    service = JobService(db)

    # --- Load job and verify state ---
    from app.models.job import Job
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        logger.error("Job not found: %s", job_id)
        return {"job_id": job_id, "status": "not_found"}

    # Idempotency: skip if already completed, failed, or cancelled
    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        logger.warning(
            "Job already %s, skipping: job_id=%s", job.status, job_id
        )
        return {"job_id": job_id, "status": job.status}

    # M-05 FIX: Reject jobs that have been queued too long (possible injection)
    max_queue_age = timedelta(hours=24)
    if hasattr(job, 'created_at') and job.created_at:
        job_age = datetime.now(timezone.utc) - job.created_at.replace(
            tzinfo=timezone.utc
        ) if job.created_at.tzinfo is None else datetime.now(
            timezone.utc
        ) - job.created_at
        if job_age > max_queue_age:
            logger.warning(
                "Job expired in queue (age=%s): job_id=%s — possible injection",
                job_age, job_id,
            )
            service.update_job_status(
                job_id, JobStatus.FAILED,
                error_message="Job expired in queue (older than 24 hours)",
            )
            return {"job_id": job_id, "status": "expired"}

    # --- Mark as processing ---
    service.update_job_status(job_id, JobStatus.PROCESSING, progress=0)

    # Load the video record
    video = db.query(Video).filter(Video.id == job.video_id).first()
    if not video:
        service.update_job_status(
            job_id, JobStatus.FAILED, error_message="Video record not found"
        )
        return {"job_id": job_id, "status": "failed"}

    video_path = video.raw_video_path
    temp_files = []

    try:
        # --- Disk space check (R7) ---
        upload_dir = os.path.dirname(video_path)
        disk_usage = shutil.disk_usage(upload_dir)
        if disk_usage.free < MIN_FREE_DISK_BYTES:
            raise RuntimeError(
                f"Insufficient disk space: {disk_usage.free / (1024**3):.1f} GB free, "
                f"need at least {MIN_FREE_DISK_BYTES / (1024**3):.0f} GB"
            )

        from app.utils.ffmpeg_utils import (
            extract_audio,
            detect_silence,
            cut_video,
            resize_video,
            get_video_info,
        )
        from app.utils.file_utils import cleanup_temp_files

        # ── Step 1: Get video info (5%) ──
        _check_cancelled(db, job_id, temp_files)
        logger.info("Step 1/5: Getting video info — %s", video_path)
        service.update_job_status(job_id, JobStatus.PROCESSING, progress=5)
        video_info = get_video_info(video_path)
        duration = float(video_info.get("format", {}).get("duration", 0))

        # ── Step 2: Extract audio (20%) ──
        _check_cancelled(db, job_id, temp_files)
        logger.info("Step 2/5: Extracting audio — %s", video_path)
        service.update_job_status(job_id, JobStatus.PROCESSING, progress=20)
        with ffmpeg_semaphore:
            audio_path = extract_audio(video_path)
        temp_files.append(audio_path)

        # ── Step 3: Detect silence (40%) ──
        _check_cancelled(db, job_id, temp_files)
        logger.info("Step 3/5: Detecting silence — %s", audio_path)
        service.update_job_status(job_id, JobStatus.PROCESSING, progress=40)
        with ffmpeg_semaphore:
            silences = detect_silence(audio_path)

        # Build non-silent segments as clips
        clips_timestamps = _build_clip_timestamps(silences, duration)

        if not clips_timestamps:
            # No silent segments found — use the full video
            clips_timestamps = [{"start": 0.0, "end": duration}]

        # ── Step 4: Cut and resize clips (60-80%) ──
        _check_cancelled(db, job_id, temp_files)
        logger.info(
            "Step 4/5: Cutting %d clips — %s", len(clips_timestamps), video_path
        )
        service.update_job_status(job_id, JobStatus.PROCESSING, progress=60)

        output_dir = os.path.join(
            os.path.dirname(video_path), "outputs", job_id
        )
        os.makedirs(output_dir, exist_ok=True)

        clip_paths = []
        with ffmpeg_semaphore:
            clip_paths = cut_video(video_path, clips_timestamps, output_dir)

        # Resize each clip to 9:16 vertical format
        resized_paths = []
        for i, clip_path in enumerate(clip_paths):
            progress = 60 + int((i / max(len(clip_paths), 1)) * 20)
            _check_cancelled(db, job_id, temp_files)
            service.update_job_status(job_id, JobStatus.PROCESSING, progress=progress)

            resized_path = None
            with ffmpeg_semaphore:
                resized_path = resize_video(clip_path, resolution="1080x1920")
            resized_paths.append(resized_path)
            # Mark original clip for cleanup (keep resized)
            temp_files.append(clip_path)

        # ── Step 5: Save outputs to database (90-100%) ──
        _check_cancelled(db, job_id, temp_files)
        logger.info("Step 5/5: Saving %d outputs to database", len(resized_paths))
        service.update_job_status(job_id, JobStatus.PROCESSING, progress=90)

        for resized_path in resized_paths:
            file_size = os.path.getsize(resized_path) if os.path.exists(resized_path) else None
            output_record = Output(
                video_id=video.id,
                file_url=resized_path,
                resolution="1080x1920",
                duration=None,  # Could be calculated per clip
                file_size_bytes=file_size,
            )
            db.add(output_record)

        db.commit()

        # ── Mark as completed ──
        service.update_job_status(job_id, JobStatus.COMPLETED, progress=100)
        video.status = VideoStatus.COMPLETED
        db.commit()

        # Clean up temp files (audio, unresized clips)
        cleanup_temp_files(*temp_files)

        logger.info(
            "Task completed: job_id=%s outputs=%d", job_id, len(resized_paths)
        )
        return {
            "job_id": job_id,
            "status": "completed",
            "output_count": len(resized_paths),
        }

    except _CancelledError:
        # Job was cancelled — already handled by _check_cancelled
        return {"job_id": job_id, "status": "cancelled"}

    except Exception as exc:
        db.rollback()

        # Determine if this error is retriable
        import subprocess
        from sqlalchemy.exc import OperationalError
        retriable = isinstance(exc, (
            subprocess.CalledProcessError,  # FFmpeg crash
            subprocess.TimeoutExpired,      # FFmpeg hang
            ConnectionError,                # Redis/network
            OperationalError,               # Database connection
            OSError,                        # Filesystem transient
        ))

        # Retry only retriable errors
        if retriable and self.request.retries < self.max_retries:
            logger.warning(
                "Task failed (will retry): job_id=%s attempt=%d error=%s",
                job_id, self.request.retries + 1, str(exc),
            )
            # Clean up temp files before retry
            from app.utils.file_utils import cleanup_temp_files
            cleanup_temp_files(*temp_files)

            raise self.retry(exc=exc)

        # All retries exhausted — mark as failed
        logger.error(
            "Task failed permanently: job_id=%s error=%s", job_id, str(exc)
        )
        try:
            service.update_job_status(
                job_id,
                JobStatus.FAILED,
                progress=job.progress if job else 0,
                error_message=str(exc)[:1000],
            )
            video = db.query(Video).filter(Video.id == job.video_id).first()
            if video:
                video.status = VideoStatus.FAILED
                db.commit()
        except Exception as db_exc:
            logger.error("Failed to update job status: %s", db_exc)

        # Clean up temp files
        from app.utils.file_utils import cleanup_temp_files
        cleanup_temp_files(*temp_files)

        return {"job_id": job_id, "status": "failed", "error": str(exc)[:500]}


class _CancelledError(Exception):
    """Sentinel exception raised when a job has been cancelled.

    This is NOT an error — it's a clean exit signal. It's caught
    separately from retried exceptions and does not trigger retries.
    """
    pass


def _check_cancelled(db, job_id: str, temp_files: list) -> None:
    """Check if the job has been cancelled or failed externally.

    Called between pipeline steps to enable responsive cancellation
    and safe handling of stale job recovery.

    Refreshes only the target job's status from DB (not all objects)
    to pick up external cancel requests or stale-job-recovery changes.

    Args:
        db: Active database session.
        job_id: The job UUID to check.
        temp_files: List of temp files to clean up on abort.

    Raises:
        _CancelledError: If the job status is CANCELLED or FAILED.
    """
    from app.models.job import Job
    from app.models.enums import JobStatus

    # Refresh only this specific job (M2 fix: avoid expensive expire_all)
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        db.refresh(job)

    # H4 Fix: Also abort on FAILED (set by stale recovery task)
    if job and job.status in (JobStatus.CANCELLED, JobStatus.FAILED):
        reason = "cancelled by user" if job.status == JobStatus.CANCELLED else "marked failed by recovery system"
        logger.info("Job %s, aborting: job_id=%s", reason, job_id)
        # Clean up any temp files created so far
        from app.utils.file_utils import cleanup_temp_files
        cleanup_temp_files(*temp_files)
        raise _CancelledError(f"Job {job_id} was {reason}")


def _build_clip_timestamps(
    silences: list[dict],
    total_duration: float,
    min_clip_duration: float = 2.0,
) -> list[dict]:
    """Build non-silent clip timestamps from silence detection results.

    Takes the gaps between silent segments and returns them as clips,
    filtering out clips shorter than min_clip_duration.

    Args:
        silences: List of {"start": float, "end": float} silent segments.
        total_duration: Total duration of the source video in seconds.
        min_clip_duration: Minimum clip length to keep (seconds).

    Returns:
        List of {"start": float, "end": float} for non-silent segments.
    """
    if not silences:
        return []

    clips = []
    prev_end = 0.0

    for silence in sorted(silences, key=lambda s: s["start"]):
        start = silence["start"]
        end = silence["end"]

        # Non-silent segment between previous end and this silence start
        if start - prev_end >= min_clip_duration:
            clips.append({"start": prev_end, "end": start})

        prev_end = end

    # Final segment after last silence
    if total_duration - prev_end >= min_clip_duration:
        clips.append({"start": prev_end, "end": total_duration})

    return clips

"""
Maintenance Celery tasks.

Scheduled tasks for system health and cleanup:
- Stale job recovery: Finds stuck "processing" jobs and marks them failed.
- Orphan file cleanup: Removes temporary files left by crashed workers.

These tasks run via Celery Beat on a fixed schedule and do NOT
contain business logic — they only query the database and filesystem.
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone

from celery.utils.log import get_task_logger

from workers.celery_app import celery_app

logger = get_task_logger(__name__)


# ─────────────────────────────────────────────────────
# 1. STALE JOB RECOVERY
# ─────────────────────────────────────────────────────

@celery_app.task(
    name="workers.tasks.maintenance_tasks.recover_stale_jobs",
    ignore_result=True,
)
def recover_stale_jobs(threshold_minutes: int = 60) -> dict:
    """Find and fail jobs stuck in 'processing' state.

    A job is considered stale if it has been in 'processing' status
    for longer than `threshold_minutes` without any update. This
    typically happens when a worker crashes mid-task.

    Runs every 10 minutes via Celery Beat.

    Args:
        threshold_minutes: Minutes after which a processing job
                           is considered stale. Default: 60 min.

    Returns:
        Dict with count of recovered jobs.
    """
    from workers.tasks.video_tasks import _get_db_session
    from app.models.job import Job
    from app.models.enums import JobStatus

    db = _get_db_session()
    recovered = 0

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)

        stale_jobs = (
            db.query(Job)
            .filter(
                Job.status == JobStatus.PROCESSING,
                Job.updated_at < cutoff,
            )
            .all()
        )

        if not stale_jobs:
            logger.info("Stale job recovery: no stale jobs found")
            return {"recovered": 0}

        for job in stale_jobs:
            job.status = JobStatus.FAILED
            job.error_message = (
                f"Job timed out: no progress for {threshold_minutes} minutes. "
                f"Last updated at {job.updated_at.isoformat()}. "
                f"Automatically marked as failed by recovery system."
            )
            recovered += 1
            logger.warning(
                "Stale job recovered: job_id=%s last_updated=%s",
                job.id, job.updated_at,
            )

        db.commit()
        logger.info("Stale job recovery complete: %d jobs recovered", recovered)

    except Exception as exc:
        db.rollback()
        logger.error("Stale job recovery failed: %s", exc)
    finally:
        db.close()

    return {"recovered": recovered}


# ─────────────────────────────────────────────────────
# 2. ORPHAN TEMPORARY FILE CLEANUP
# ─────────────────────────────────────────────────────

# File patterns that indicate temporary/intermediate files
_TEMP_PATTERNS = (".wav", "_clip_")

# Files must be older than this to be eligible for cleanup
_CLEANUP_AGE_HOURS = 2


@celery_app.task(
    name="workers.tasks.maintenance_tasks.cleanup_orphan_files",
    ignore_result=True,
)
def cleanup_orphan_files() -> dict:
    """Remove orphaned temporary files from the uploads directory.

    Scans all user upload directories for temporary files (audio WAV,
    intermediate clips) that are older than 2 hours. These files are
    leftovers from crashed or interrupted workers.

    Safety: Only deletes files matching known temp patterns AND older
    than the age threshold. Active processing files (< 2 hours old)
    are never touched.

    Runs every 1 hour via Celery Beat.

    Returns:
        Dict with count of cleaned files and reclaimed bytes.
    """
    from app.config import get_settings

    settings = get_settings()
    upload_dir = settings.upload_dir
    cleaned = 0
    reclaimed_bytes = 0
    cutoff = time.time() - (_CLEANUP_AGE_HOURS * 3600)

    if not os.path.exists(upload_dir):
        logger.info("Orphan cleanup: upload directory does not exist, skipping")
        return {"cleaned": 0, "reclaimed_bytes": 0}

    try:
        for root, dirs, files in os.walk(upload_dir):
            for filename in files:
                # Check if filename matches temp patterns
                is_temp = any(pattern in filename for pattern in _TEMP_PATTERNS)
                if not is_temp:
                    continue

                filepath = os.path.join(root, filename)
                try:
                    file_mtime = os.path.getmtime(filepath)
                    if file_mtime < cutoff:
                        file_size = os.path.getsize(filepath)
                        os.remove(filepath)
                        cleaned += 1
                        reclaimed_bytes += file_size
                        logger.debug("Cleaned orphan file: %s (%d bytes)", filepath, file_size)
                except OSError as exc:
                    # File may be in use by an active worker — skip
                    logger.debug("Cannot clean file (in use?): %s — %s", filepath, exc)

        if cleaned > 0:
            logger.info(
                "Orphan cleanup complete: %d files removed, %.1f MB reclaimed",
                cleaned, reclaimed_bytes / (1024 * 1024),
            )
        else:
            logger.info("Orphan cleanup: no orphan files found")

    except Exception as exc:
        logger.error("Orphan cleanup failed: %s", exc)

    return {"cleaned": cleaned, "reclaimed_bytes": reclaimed_bytes}

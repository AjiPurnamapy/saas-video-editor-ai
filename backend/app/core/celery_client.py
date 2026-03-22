"""
Celery task dispatcher.

S-23 FIX: Provides a lightweight Celery client that uses send_task()
with string-based task names instead of importing directly from the
workers/ package. This eliminates the need for sys.path manipulation
in any backend module.

Usage:
    from app.core.celery_client import dispatch_task, revoke_task

    result = dispatch_task("workers.tasks.video_tasks.process_video", args=[job_id])
    revoke_task(task_id)
"""

import logging

from celery import Celery

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Lightweight Celery client — shares the same broker as workers
# but does NOT import any worker task modules
celery_client = Celery(
    "ai_video_editor",
    broker=settings.redis_url,
)


def dispatch_task(task_name: str, args: list | None = None) -> str:
    """Dispatch a task to the Celery worker queue by name.

    Args:
        task_name: Fully qualified task name (e.g. "workers.tasks.video_tasks.process_video").
        args: Positional arguments to pass to the task.

    Returns:
        The Celery AsyncResult ID (task_id).
    """
    result = celery_client.send_task(task_name, args=args or [])
    logger.info("Task dispatched: name=%s task_id=%s", task_name, result.id)
    return result.id


def revoke_task(task_id: str) -> None:
    """Revoke (cancel) a running or queued task.

    Args:
        task_id: The Celery task ID to revoke.
    """
    celery_client.control.revoke(task_id, terminate=False)
    logger.info("Task revoked: task_id=%s", task_id)

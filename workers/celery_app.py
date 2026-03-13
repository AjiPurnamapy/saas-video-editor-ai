"""
Celery application configuration.

Provides a configured Celery instance using Redis as both the
message broker and result backend. All workers import this module
to get the shared Celery app.

Usage:
    celery -A workers.celery_app worker --loglevel=info
"""

import os
import sys
import logging
import threading

from celery import Celery
from kombu import Queue

# Ensure the backend package is importable by workers
# (workers/ is at the same level as backend/)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_backend_dir = os.path.join(_project_root, "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.config import get_settings
from app.core.logging_config import setup_logging

settings = get_settings()

# Initialize structured logging for workers
setup_logging(
    level="DEBUG" if settings.app_debug else "INFO",
    json_format=settings.app_env != "development",
)

logger = logging.getLogger(__name__)

# --- FFmpeg Concurrency Limiter (R1) ---
# Limits concurrent FFmpeg subprocesses per worker to prevent
# CPU/RAM exhaustion. Each FFmpeg resize uses ~1.5 GB RAM.
# Value should be <= number of CPU cores available to this worker.
MAX_CONCURRENT_FFMPEG = int(os.environ.get("MAX_CONCURRENT_FFMPEG", "2"))
ffmpeg_semaphore = threading.Semaphore(MAX_CONCURRENT_FFMPEG)
logger.info("FFmpeg concurrency limit set to %d", MAX_CONCURRENT_FFMPEG)

# --- Celery App ---
celery_app = Celery(
    "ai_video_editor",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# --- Celery Configuration ---
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task defaults
    task_acks_late=True,            # Acknowledge AFTER task completes (crash safety)
    task_reject_on_worker_lost=True,  # Requeue if worker dies mid-task
    worker_prefetch_multiplier=1,   # Fetch one task at a time (fair scheduling)

    # Broker connection (R2 — fix Celery 6.0 deprecation)
    broker_connection_retry_on_startup=True,

    # Worker resource guards
    worker_max_tasks_per_child=50,      # Restart worker after 50 tasks (prevent memory leak)
    worker_max_memory_per_child=2_000_000,  # Restart if worker RAM > ~2 GB (kB)

    # Result expiration
    result_expires=86400,           # Results expire after 24 hours

    # Task routing — priority queues
    task_default_queue="default",
    task_routes={
        "workers.tasks.video_tasks.*": {"queue": "default"},
        "workers.tasks.maintenance_tasks.*": {"queue": "default"},
    },

    # Queue definitions for priority scheduling
    # Workers subscribe to queues: celery -Q high_priority,default,low_priority
    task_queues=(
        Queue("high_priority", routing_key="high_priority"),
        Queue("default", routing_key="default"),
        Queue("low_priority", routing_key="low_priority"),
    ),

    # Retry defaults (can be overridden per-task)
    task_default_retry_delay=10,    # 10 seconds initial retry delay
    task_max_retries=3,

    # --- Celery Beat Schedule ---
    beat_schedule={
        "recover-stale-jobs": {
            "task": "workers.tasks.maintenance_tasks.recover_stale_jobs",
            "schedule": 600.0,  # Every 10 minutes
            "options": {"queue": "default"},
        },
        "cleanup-orphan-files": {
            "task": "workers.tasks.maintenance_tasks.cleanup_orphan_files",
            "schedule": 3600.0,  # Every 1 hour
            "options": {"queue": "default"},
        },
    },
)

# Explicitly discover tasks in workers/tasks/
celery_app.autodiscover_tasks(["workers.tasks"], related_name="video_tasks")
celery_app.autodiscover_tasks(["workers.tasks"], related_name="maintenance_tasks")

# Explicitly import to guarantee registration
import workers.tasks.video_tasks  # noqa
import workers.tasks.maintenance_tasks  # noqa

logger.info("Celery app configured: broker=%s", settings.redis_url)

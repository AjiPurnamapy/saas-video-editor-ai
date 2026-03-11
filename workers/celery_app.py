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

from celery import Celery

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

    # Result expiration
    result_expires=86400,           # Results expire after 24 hours

    # Task routing
    task_default_queue="default",
    task_routes={
        "workers.tasks.video_tasks.*": {"queue": "video_processing"},
    },

    # Retry defaults (can be overridden per-task)
    task_default_retry_delay=10,    # 10 seconds initial retry delay
    task_max_retries=3,
)

# Auto-discover tasks in workers/tasks/
celery_app.autodiscover_tasks(["workers.tasks"])

logger.info("Celery app configured: broker=%s", settings.redis_url)

"""
Progress publisher module.

Publishes real-time job progress updates to Redis Pub/Sub channels.
The SSE endpoint subscribes to these channels to stream updates to clients.

Each job gets its own channel: ``progress:{job_id}``

Message format (JSON):
    {
        "job_id": "...",
        "status": "processing",
        "progress": 42,
        "step": "Extracting audio",
        "timestamp": "2026-03-21T01:30:00Z"
    }
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import redis

from app.config import get_settings

logger = logging.getLogger(__name__)

PROGRESS_CHANNEL_PREFIX = "progress:"

# Singleton publisher connection (separate from session_manager pool)
_pub_pool: Optional[redis.ConnectionPool] = None
_pub_client: Optional[redis.Redis] = None


def _get_publisher() -> redis.Redis:
    """Get or create the Redis publisher client."""
    global _pub_pool, _pub_client
    if _pub_client is None:
        settings = get_settings()
        _pub_pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=5,
            decode_responses=True,
            socket_timeout=3,
            socket_connect_timeout=3,
        )
        _pub_client = redis.Redis(connection_pool=_pub_pool)
    return _pub_client


def publish_progress(
    job_id: str,
    status: str,
    progress: int,
    step: str = "",
    error: str = "",
) -> None:
    """Publish a progress update to the job's Redis Pub/Sub channel.

    Args:
        job_id: The job UUID.
        status: Current job status (processing, completed, failed, cancelled).
        progress: Progress percentage (0-100).
        step: Human-readable description of current pipeline step.
        error: Error message if status is 'failed'.
    """
    channel = f"{PROGRESS_CHANNEL_PREFIX}{job_id}"
    message = {
        "job_id": job_id,
        "status": status,
        "progress": progress,
        "step": step,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        client = _get_publisher()
        client.publish(channel, json.dumps(message))
        logger.debug(
            "Progress published: job=%s progress=%d%% step=%s",
            job_id, progress, step,
        )
    except Exception as exc:
        # Non-critical — don't crash the worker if Redis pub fails
        logger.warning("Failed to publish progress: job=%s error=%s", job_id, exc)

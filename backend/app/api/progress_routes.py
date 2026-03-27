"""
SSE progress routes.

Provides a Server-Sent Events (SSE) endpoint for real-time job
progress streaming. Clients connect to ``GET /jobs/{job_id}/progress``
and receive a continuous stream of progress events via Redis Pub/Sub.

SSE is preferred over WebSocket here because:
- Unidirectional (server → client) is sufficient for progress
- Works through HTTP proxies and CDNs without special config
- Automatic reconnection built into the browser EventSource API
- Simpler to implement and debug
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.config import get_settings
from app.core.auth import get_current_user
from app.core.progress_publisher import PROGRESS_CHANNEL_PREFIX
from app.core.rate_limiter import limiter
from app.database import get_db
from app.models.user import User
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])
logger = logging.getLogger(__name__)

# --- Shared async Redis connection pool for SSE subscribers ---
# Prevents per-request connection exhaustion under moderate load.
# All SSE generators reuse connections from this pool.
_sse_redis_pool: Optional[aioredis.Redis] = None


def _get_sse_redis() -> aioredis.Redis:
    """Get or create the shared async Redis client for SSE subscribers."""
    global _sse_redis_pool
    if _sse_redis_pool is None:
        settings = get_settings()
        _sse_redis_pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,  # Shared across all SSE connections
        )
    return _sse_redis_pool


async def _progress_event_generator(
    job_id: str,
    request: Request,
) -> AsyncGenerator[dict, None]:
    """Generate SSE events from Redis Pub/Sub for a specific job.

    Yields progress events until the job completes, fails, or
    the client disconnects.

    Args:
        job_id: The job UUID to subscribe to.
        request: FastAPI request — used to detect client disconnect.

    Yields:
        Dict with 'event' and 'data' keys for SSE formatting.
    """
    channel = f"{PROGRESS_CHANNEL_PREFIX}{job_id}"
    r = _get_sse_redis()
    pubsub = r.pubsub()

    try:
        await pubsub.subscribe(channel)
        logger.info("SSE client subscribed: job=%s", job_id)

        # Send initial connection event
        yield {
            "event": "connected",
            "data": json.dumps({"job_id": job_id, "message": "Subscribed to progress"}),
        }

        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info("SSE client disconnected: job=%s", job_id)
                break

            # Poll for messages (non-blocking with timeout)
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )

            if message and message["type"] == "message":
                data = message["data"]
                try:
                    parsed = json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    parsed = {"raw": data}

                yield {
                    "event": "progress",
                    "data": json.dumps(parsed),
                }

                # Close stream on terminal statuses
                terminal_statuses = {"completed", "failed", "cancelled"}
                if parsed.get("status") in terminal_statuses:
                    logger.info(
                        "SSE stream closing (terminal): job=%s status=%s",
                        job_id, parsed.get("status"),
                    )
                    break
            else:
                # No message — send heartbeat to keep connection alive
                await asyncio.sleep(1)
                yield {"event": "heartbeat", "data": ""}

    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        # NOTE: Do NOT close `r` — it's the shared pool, not a per-request client
        logger.info("SSE cleanup complete: job=%s", job_id)


@router.get(
    "/{job_id}/progress",
    summary="Stream job progress via SSE",
    responses={
        200: {"description": "SSE event stream"},
        404: {"description": "Job not found"},
    },
)
@limiter.limit("30/minute")
async def stream_job_progress(
    request: Request,
    response: Response,
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream real-time job progress updates via Server-Sent Events.

    The client should use the browser's ``EventSource`` API or
    ``fetch()`` with a ReadableStream to consume this endpoint::

        const evtSource = new EventSource('/api/jobs/{job_id}/progress');
        evtSource.addEventListener('progress', (e) => {
            const data = JSON.parse(e.data);
            console.log(data.progress, data.step);
        });

    Events:
        - ``connected``: Initial connection confirmation
        - ``progress``: Job progress update (status, progress %, step name)
        - ``heartbeat``: Keep-alive (every ~1 second when idle)

    The stream automatically closes when the job reaches a terminal
    status (completed, failed, cancelled) or the client disconnects.

    Rate limited to 30 SSE connections per minute.

    Args:
        request: FastAPI request (for client disconnect detection + rate limiting).
        job_id: The job UUID to stream progress for.
        db: Database session (injected).
        current_user: The authenticated user (injected).

    Returns:
        An SSE event stream.
    """
    # Verify ownership
    service = JobService(db)
    job = service.get_job(job_id, current_user.id)  # raises NotFoundError

    # If already terminal, return final status as single event
    terminal = {"completed", "failed", "cancelled"}
    if job.status in terminal:
        async def _single_event():
            yield {
                "event": "progress",
                "data": json.dumps({
                    "job_id": job_id,
                    "status": job.status,
                    "progress": job.progress,
                    "step": "Finished",
                }),
            }
        return EventSourceResponse(_single_event())

    generator = _progress_event_generator(job_id, request)
    return EventSourceResponse(generator)

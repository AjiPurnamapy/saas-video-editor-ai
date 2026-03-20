"""
FastAPI application entry point.

Configures the application with CORS, rate limiting, structured logging,
routers, and exception handlers. This is the module that uvicorn loads.
"""

import logging
import os
import traceback
import uuid as _uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.core.exceptions import AppError
from app.core.logging_config import setup_logging
from app.core.rate_limiter import limiter
from app.core.csrf import verify_csrf_token
from app.api.auth_routes import router as auth_router
from app.api.video_routes import router as video_router
from app.api.job_routes import router as job_router
from app.api.output_routes import router as output_router

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    Runs startup and shutdown logic. Initializes logging and
    creates the upload directory on startup.
    """
    # Configure structured logging
    log_level = "DEBUG" if settings.app_debug else "INFO"
    json_format = settings.app_env != "development"
    setup_logging(level=log_level, json_format=json_format)

    # Create upload directory
    os.makedirs(settings.upload_dir, exist_ok=True)

    logger.info(
        "Application starting: app=%s env=%s",
        settings.app_name, settings.app_env,
    )
    yield
    logger.info("Application shutting down")


# --- Application Factory ---
def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A fully configured FastAPI application instance.
    """
    application = FastAPI(
        title=settings.app_name,
        description=(
            "AI-powered video editing SaaS platform. "
            "Upload raw videos and automatically generate edited "
            "short-form content for TikTok, Reels, and Shorts."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # --- Middleware ---
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        # M-03 FIX: Only allow methods and headers actually needed
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-CSRF-Token",
            "X-Request-ID",
        ],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )

    # Rate limiting
    application.state.limiter = limiter
    application.add_exception_handler(
        RateLimitExceeded,
        _rate_limit_exceeded_handler,
    )

    # --- Domain Exception Handler ---
    @application.exception_handler(AppError)
    async def app_error_handler(
        request: Request,
        exc: AppError,
    ) -> JSONResponse:
        """Convert domain exceptions to clean JSON responses.

        All services raise AppError subclasses (NotFoundError,
        ConflictError, etc.) which carry their own status_code
        and detail message.
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    # --- H-01 FIX: CSRF Middleware ---
    @application.middleware("http")
    async def csrf_middleware(request: Request, call_next):
        """Validate CSRF token on state-changing API requests."""
        if request.url.path.startswith("/api/"):
            try:
                verify_csrf_token(request)
            except Exception as exc:
                return JSONResponse(
                    status_code=exc.status_code if hasattr(exc, 'status_code') else 403,
                    content={"detail": str(exc.detail) if hasattr(exc, 'detail') else "CSRF validation failed"},
                )
        return await call_next(request)

    # --- H-02 FIX: Hardened Global Exception Handler ---
    @application.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Catch unhandled exceptions and return a clean 500 response.

        NEVER exposes exception details to the client.
        Generates an incident_id for log correlation instead.
        """
        # Generate incident ID for log <-> support ticket correlation
        incident_id = _uuid.uuid4().hex[:12]

        # Log FULL details server-side (never sent to client)
        logger.error(
            "Unhandled exception: %s %s | incident=%s\n%s",
            request.method,
            request.url,
            incident_id,
            traceback.format_exc(),
        )

        # Client gets incident_id only — no internal details
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "incident_id": incident_id,
            },
        )

    # --- Routers ---
    application.include_router(auth_router, prefix="/api")
    application.include_router(video_router, prefix="/api")
    application.include_router(job_router, prefix="/api")
    application.include_router(output_router, prefix="/api")

    # --- Health Check ---
    @application.get("/health", tags=["Health"])
    async def health_check() -> dict:
        """Health check endpoint for load balancers and monitoring.

        Verifies connectivity to PostgreSQL and Redis.
        Returns individual component statuses and an overall status.
        """
        result = {
            "status": "healthy",
            "app": settings.app_name,
            "version": "0.1.0",
            "components": {},
        }

        # Check database connectivity
        try:
            from app.database import engine
            with engine.connect() as conn:
                conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            result["components"]["database"] = "ok"
        except Exception as exc:
            logger.error("Health check — database failed: %s", exc)
            result["components"]["database"] = "error"
            result["status"] = "degraded"

        # Check Redis connectivity
        try:
            from app.core.session_manager import _redis_client
            _redis_client.ping()
            result["components"]["redis"] = "ok"
        except Exception as exc:
            logger.error("Health check — redis failed: %s", exc)
            result["components"]["redis"] = "error"
            result["status"] = "degraded"

        return result

    return application


# Create the application instance (used by uvicorn)
app = create_app()

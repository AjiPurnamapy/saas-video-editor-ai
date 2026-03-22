"""
Application configuration module.

Loads settings from environment variables using pydantic-settings.
All configuration is centralized here for easy management.

SECURITY:
- C-01: secret_key validated at startup to prevent insecure defaults
- C-01: cookie_secure enforced in production (HTTPS required)
- M-03: cors_origins validated to block wildcard and HTTP in production
- L-04: secret_key_previous supports key rotation without mass logout
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Application ---
    app_name: str = "AI Video Editor"
    app_env: str = "development"
    app_debug: bool = False

    # --- Database ---
    database_url: str = "postgresql://postgres:postgres@localhost:5432/ai_video_editor"
    database_echo: bool = False

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Security ---
    secret_key: str = "change-me-to-a-random-64-char-string"
    # L-04 FIX: Previous key for rotation — sessions signed with this key
    # remain valid during transition. Set to None when rotation is complete.
    secret_key_previous: Optional[str] = None
    session_cookie_name: str = "session_id"
    session_max_age_seconds: int = 86400  # 24 hours
    cookie_secure: bool = False  # Set True in production (HTTPS)
    cookie_domain: str = "localhost"

    # --- CORS ---
    cors_origins: List[str] = ["http://localhost:3000"]

    # --- Storage (S3-compatible) ---
    storage_bucket: str = "ai-video-editor"
    storage_endpoint_url: str = "http://localhost:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_region: str = "us-east-1"

    # --- Uploads ---
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 500

    # --- Email / SMTP ---
    smtp_host: str = ""          # Empty = dev mode (log to console)
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@aivideoeditor.com"

    # --- Frontend ---
    frontend_url: str = "http://localhost:3000"

    # ---- C-01 FIX: Validate security settings at startup ----

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Block startup if secret_key is insecure in non-development environments."""
        insecure_defaults = {
            "change-me-to-a-random-64-char-string",
            "secret",
            "dev",
            "",
        }
        env = os.getenv("APP_ENV", "development")
        # Only enforce in non-development environments
        if env not in ("development", "testing") and v in insecure_defaults:
            raise ValueError(
                "SECRET_KEY must not use a default value in production/staging. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(64))\""
            )
        if env not in ("development", "testing") and len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters.")
        return v

    @field_validator("cookie_secure")
    @classmethod
    def validate_cookie_secure(cls, v: bool) -> bool:
        """Enforce secure cookies in production (requires HTTPS)."""
        env = os.getenv("APP_ENV", "development")
        if env == "production" and not v:
            raise ValueError(
                "COOKIE_SECURE must be True in production (requires HTTPS)."
            )
        return v

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: list) -> list:
        """M-03 FIX: Block wildcard and non-HTTPS origins in production."""
        env = os.getenv("APP_ENV", "development")
        if env == "production":
            for origin in v:
                if origin == "*":
                    raise ValueError(
                        "CORS wildcard '*' is not allowed in production"
                    )
                if not origin.startswith("https://"):
                    raise ValueError(
                        f"CORS origins must use HTTPS in production: {origin}"
                    )
        return v

    model_config = {
        # Check current dir first, then parent dir for root .env
        "env_file": (".env", "../.env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",  # Important: Ignore env vars not defined in this class
    }


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton.

    Returns:
        Settings: The application settings instance.
    """
    return Settings()

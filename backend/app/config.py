"""
Application configuration module.

Loads settings from environment variables using pydantic-settings.
All configuration is centralized here for easy management.
"""

from functools import lru_cache
from typing import List

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

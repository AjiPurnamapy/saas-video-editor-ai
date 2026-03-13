"""
Database module.

Provides SQLAlchemy engine, session factory, and a dependency
for injecting database sessions into FastAPI route handlers.
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# SQLAlchemy engine — connection pool to PostgreSQL
# NOTE: This pool is used by the API server only.
# Celery workers use a separate, dedicated pool defined in
# workers/tasks/video_tasks.py to prevent connection exhaustion.
engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,   # Verify connections before use
    pool_recycle=1800,     # Recycle connections every 30 min
)

# Session factory — creates new database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a database session.

    Yields a SQLAlchemy session and ensures it is closed after the
    request completes, even if an exception occurs.

    Yields:
        Session: A SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

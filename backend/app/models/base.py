"""
SQLAlchemy declarative base.

All models inherit from this Base class. Using the DeclarativeBase
approach from SQLAlchemy 2.0 for modern type-annotated models.

Uses native UUID type for primary keys (4x smaller, faster joins
compared to storing UUIDs as strings).
"""

import uuid as _uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Abstract base class for all database models."""

    pass


class TimestampMixin:
    """Mixin that adds created_at timestamp to models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """Mixin that adds a native UUID primary key to models.

    Uses SQLAlchemy's Uuid type which maps to PostgreSQL's native
    UUID column (16 bytes vs 36 bytes for varchar). This provides:
    - 4x smaller storage
    - Faster index lookups and joins
    - Proper type safety at the database level
    """

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda: str(_uuid.uuid4()),
    )

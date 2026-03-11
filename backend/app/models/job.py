"""
Job model.

Represents a video processing job. Tracks the state and progress
of async video processing tasks executed by Celery workers.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import JobStatus


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Video processing job model."""

    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_video_status", "video_id", "status"),
    )

    video_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        Enum(JobStatus, name="job_status", values_callable=lambda e: [s.value for s in e]),
        default=JobStatus.QUEUED,
        nullable=False,
        index=True,
    )
    progress: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    task_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Celery task ID for tracking the async worker process",
    )

    # Relationships
    video = relationship("Video", back_populates="jobs")

    def __repr__(self) -> str:
        return f"<Job id={self.id} status={self.status} progress={self.progress}%>"

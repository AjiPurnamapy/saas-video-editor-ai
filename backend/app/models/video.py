"""
Video model.

Represents an uploaded raw video file. Each video belongs to a user
and can have multiple processing jobs and output files.
"""

from typing import Optional

from sqlalchemy import Enum, Float, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import VideoStatus


class Video(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Uploaded video model."""

    __tablename__ = "videos"
    __table_args__ = (
        Index("ix_videos_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_video_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    original_filename: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    duration: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        Enum(VideoStatus, name="video_status", values_callable=lambda e: [s.value for s in e]),
        default=VideoStatus.UPLOADED,
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="videos")
    jobs = relationship("Job", back_populates="video", cascade="all, delete-orphan")
    outputs = relationship("Output", back_populates="video", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Video id={self.id} status={self.status}>"

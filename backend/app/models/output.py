"""
Output model.

Represents a processed/exported video file produced by the
video editing pipeline.
"""

from typing import Optional

from sqlalchemy import Float, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Output(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Processed video output model."""

    __tablename__ = "outputs"
    __table_args__ = (
        Index("ix_outputs_video_created", "video_id", "created_at"),
    )

    video_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )
    resolution: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    duration: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        nullable=True,
    )

    # Relationships
    video = relationship("Video", back_populates="outputs")

    def __repr__(self) -> str:
        return f"<Output id={self.id} resolution={self.resolution}>"

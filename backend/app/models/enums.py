"""
Status enumerations.

Defines Python enums for all status fields used across models.
These are used both as Python-side constants and as database-level
constraints (via SQLAlchemy's Enum type).
"""

import enum


class VideoStatus(str, enum.Enum):
    """Status values for the Video model."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(str, enum.Enum):
    """Status values for the Job model."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

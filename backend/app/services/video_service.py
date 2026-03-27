"""
Video service.

Business logic for video upload, retrieval, and deletion.
Coordinates between the database and storage layer.

SECURITY:
- Uploads use chunked streaming (never loads full file into RAM)
- Filenames are sanitized to prevent path traversal
- Resolved paths are validated to stay within the upload directory
- C-03 FIX: Upload paths hashed with SHA-256 + directory sharding
"""

import hashlib
import logging
import os
import uuid
from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions import (
    FileTooLargeError,
    NotFoundError,
    ValidationError,
)
from app.models.enums import VideoStatus
from app.models.video import Video
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)
settings = get_settings()

# Chunk size for streaming uploads (1 MB)
UPLOAD_CHUNK_SIZE = 1024 * 1024

# H-05 FIX: Minimum file size to prevent invalid/empty uploads
MIN_FILE_SIZE_BYTES = 1024 * 10  # 10KB — no valid video is smaller
MAX_FILENAME_LENGTH = 255

# Known magic byte signatures for video files
_VIDEO_SIGNATURES = [
    (4, b"ftyp"),       # MP4, MOV, M4V, 3GP (ISO Base Media)
    (0, b"RIFF"),       # AVI (and WAV, but content-type check filters)
    (0, b"\x1a\x45\xdf\xa3"),  # MKV / WebM (EBML header)
    (0, b"\x00\x00\x01\xba"),  # MPEG-PS
    (0, b"\x00\x00\x01\xb3"),  # MPEG-1/2 video
    (0, b"\x47"),       # MPEG-TS (sync byte)
]


def _validate_file_magic(header: bytes) -> bool:
    """Check if file header matches known video magic bytes.

    This is a defense-in-depth measure against content-type spoofing.
    A malicious user could set content_type to 'video/mp4' but upload
    a PHP script or executable.

    Args:
        header: First 16+ bytes of the file.

    Returns:
        True if the header matches any known video signature.
    """
    for offset, signature in _VIDEO_SIGNATURES:
        end = offset + len(signature)
        if len(header) >= end and header[offset:end] == signature:
            return True
    return False


def _sanitize_filename(filename: str) -> str:
    """Strip directory components and dangerous characters from a filename.

    Prevents path traversal attacks like '../../etc/passwd'.

    Args:
        filename: The raw filename from the upload.

    Returns:
        A safe filename string (basename only, no directory traversal).
    """
    # Use os.path.basename to strip all directory components
    safe_name = os.path.basename(filename)
    # Remove null bytes
    safe_name = safe_name.replace("\x00", "")
    # Remove any remaining path separators (belt-and-suspenders)
    safe_name = safe_name.replace("/", "").replace("\\", "")
    # Fallback if nothing remains
    if not safe_name or safe_name.startswith("."):
        safe_name = "upload.mp4"
    return safe_name


def _validate_storage_path(path: str, base_dir: str) -> str:
    """Validate that a resolved path stays within the allowed base directory.

    Prevents path traversal by resolving symlinks and checking containment.

    Args:
        path: The target file path.
        base_dir: The allowed base directory (e.g., upload_dir).

    Returns:
        The validated absolute path.

    Raises:
        ValidationError: If the path escapes the base directory.
    """
    resolved = os.path.realpath(path)
    base_resolved = os.path.realpath(base_dir)
    if not resolved.startswith(base_resolved + os.sep) and resolved != base_resolved:
        logger.warning(
            "Path traversal attempt blocked: path=%s base=%s", path, base_dir
        )
        raise ValidationError("Invalid file path")
    return resolved


def _build_storage_path(user_id: str, filename: str, upload_dir: str) -> str:
    """Build an unpredictable storage path with directory sharding.

    C-03 FIX: Instead of exposing user_id directly in the path,
    we hash it with SHA-256. The first 4 hex chars create a 2-level
    shard (256 * 256 = 65,536 directories) to prevent filesystem
    bottleneck at scale.

    Structure: uploads/{shard1}/{shard2}/{user_hash}/{uuid}.ext

    Args:
        user_id: The user's UUID.
        filename: The sanitized filename (used only for extension).
        upload_dir: The base upload directory.

    Returns:
        The full storage path.
    """
    user_hash = hashlib.sha256(user_id.encode()).hexdigest()
    shard1 = user_hash[:2]
    shard2 = user_hash[2:4]

    ext = os.path.splitext(filename)[1].lower() or ".mp4"
    unique_name = f"{uuid.uuid4().hex}{ext}"

    return os.path.join(upload_dir, shard1, shard2, user_hash, unique_name)


class VideoService:
    """Encapsulates video management business logic."""

    def __init__(self, db: Session, storage: StorageService | None = None) -> None:
        """Initialize VideoService with a database session.

        Args:
            db: SQLAlchemy database session.
            storage: Optional StorageService instance for dependency injection.
                     Defaults to a new StorageService if not provided.
        """
        self.db = db
        self.storage = storage or StorageService()

    async def upload_video(
        self,
        file: UploadFile,
        user_id: str,
    ) -> Video:
        """Upload a video file and create a database record.

        Uses chunked streaming to avoid loading the entire file into memory.
        Filenames are sanitized and paths are validated to stay within
        the upload directory.

        Args:
            file: The uploaded video file.
            user_id: ID of the user uploading the video.

        Returns:
            The created Video model.

        Raises:
            ValidationError: If the file type is invalid.
            FileTooLargeError: If the file exceeds the size limit.
        """
        # H-05 FIX: Validate filename before touching filesystem
        raw_filename = file.filename or "video.mp4"
        if len(raw_filename) > MAX_FILENAME_LENGTH:
            raise ValidationError(
                f"Filename too long (max {MAX_FILENAME_LENGTH} characters)"
            )

        # Validate file type
        allowed_types = {
            "video/mp4", "video/quicktime", "video/x-msvideo",
            "video/x-matroska", "video/webm", "video/mpeg",
        }
        if file.content_type not in allowed_types:
            raise ValidationError(
                f"Unsupported file type: {file.content_type}. "
                f"Allowed: {', '.join(allowed_types)}"
            )

        # Sanitize filename and generate unique storage path
        safe_filename = _sanitize_filename(raw_filename)
        # C-03 FIX: Use hashed, sharded path instead of exposing user_id
        storage_path = _build_storage_path(user_id, safe_filename, settings.upload_dir)

        # Validate path stays within upload directory
        storage_path = _validate_storage_path(storage_path, settings.upload_dir)

        # Fix #6: Stream to temp file, then atomic rename on success
        # If process crashes mid-upload, only a .tmp file remains — no orphans
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        tmp_path = storage_path + ".tmp"

        file_size = 0
        header_buf = b""
        magic_validated = False
        try:
            with open(tmp_path, "wb") as dest:
                while True:
                    chunk = await file.read(UPLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    file_size += len(chunk)
                    if file_size > max_bytes:
                        dest.close()
                        os.remove(tmp_path)
                        raise FileTooLargeError(
                            f"File size exceeds {settings.max_upload_size_mb}MB limit"
                        )
                    # S-14 FIX: Validate magic bytes with EOF edge case handling
                    if not magic_validated:
                        header_buf += chunk
                        if len(header_buf) >= 16:
                            if not _validate_file_magic(header_buf):
                                dest.close()
                                os.remove(tmp_path)
                                raise ValidationError(
                                    "File content does not match a supported video format"
                                )
                            magic_validated = True
                    dest.write(chunk)

                # S-14 FIX: If loop ended (EOF) before 16 bytes, reject immediately
                if not magic_validated:
                    dest.close()
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                    raise ValidationError(
                        "File too small to validate — no video magic bytes found"
                    )
        except (FileTooLargeError, ValidationError):
            raise
        except Exception as exc:
            # Clean up temp file on any write failure
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            logger.error("Upload failed for user %s: %s", user_id, exc)
            raise

        # H-05 FIX: Reject files below minimum size
        if file_size < MIN_FILE_SIZE_BYTES:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise ValidationError(
                f"File too small ({file_size} bytes). "
                f"Minimum {MIN_FILE_SIZE_BYTES // 1024}KB for a valid video."
            )

        # Atomic rename: .tmp → final path (no partial files in uploads/)
        os.replace(tmp_path, storage_path)

        # --- Duration validation (Saran 2 fix) ---
        # After the file is safely on disk, probe its duration.
        # Reject videos longer than MAX_VIDEO_DURATION_SECONDS so
        # the worker is protected from multi-hour FFmpeg re-encodes.
        MAX_VIDEO_DURATION_SECONDS = 300  # 5 minutes

        try:
            from app.utils.ffmpeg_utils import get_video_duration
            duration = get_video_duration(storage_path)
            if duration > MAX_VIDEO_DURATION_SECONDS:
                os.remove(storage_path)
                raise ValidationError(
                    f"Video is too long ({duration:.0f}s). "
                    f"Maximum allowed duration is {MAX_VIDEO_DURATION_SECONDS // 60} minutes."
                )
        except (ValidationError, FileTooLargeError):
            raise
        except Exception as probe_exc:
            # If ffprobe fails (e.g. ffprobe not installed), log and allow upload
            logger.warning(
                "Could not probe video duration (skipping check): %s", probe_exc
            )

        # Create database record
        video = Video(
            user_id=user_id,
            raw_video_path=storage_path,
            original_filename=safe_filename,
            file_size_bytes=file_size,
            status=VideoStatus.UPLOADED,
        )
        self.db.add(video)
        self.db.commit()
        self.db.refresh(video)

        logger.info(
            "Video uploaded: id=%s user=%s size=%d filename=%s",
            video.id, user_id, file_size, safe_filename,
        )
        return video

    def get_video(self, video_id: str, user_id: str) -> Video:
        """Retrieve a video by ID, scoped to the requesting user.

        Args:
            video_id: The video UUID.
            user_id: The requesting user's UUID.

        Returns:
            The Video model.

        Raises:
            NotFoundError: If the video is not found.
        """
        video = (
            self.db.query(Video)
            .filter(Video.id == video_id, Video.user_id == user_id)
            .first()
        )
        if not video:
            raise NotFoundError("Video not found")
        return video

    def list_videos(self, user_id: str, skip: int = 0, limit: int = 20) -> tuple[List[Video], int]:
        """List all videos for a user with pagination.

        Args:
            user_id: The user's UUID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A tuple of (list of videos, total count).
        """
        query = self.db.query(Video).filter(Video.user_id == user_id)
        total = query.count()
        videos = (
            query
            .order_by(Video.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return videos, total

    def delete_video(self, video_id: str, user_id: str) -> None:
        """Delete a video, its output files, and all database records.

        Refuses to delete if there is an active (queued/processing) job
        to prevent file corruption while a worker is running.

        Args:
            video_id: The video UUID.
            user_id: The requesting user's UUID.

        Raises:
            NotFoundError: If the video is not found.
            ConflictError: If the video has an active processing job.
        """
        from app.core.exceptions import ConflictError
        from app.models.enums import JobStatus
        from app.models.job import Job

        video = self.get_video(video_id, user_id)

        # C2 Fix: Block delete while worker is actively processing
        active_job = (
            self.db.query(Job)
            .filter(
                Job.video_id == video_id,
                Job.status.in_([JobStatus.QUEUED, JobStatus.PROCESSING]),
            )
            .first()
        )
        if active_job:
            raise ConflictError(
                "Cannot delete video with an active processing job. "
                "Cancel the job first."
            )

        # C3 Fix: Delete output files from disk before DB cascade
        import shutil
        video_dir = os.path.dirname(video.raw_video_path)
        outputs_dir = os.path.join(video_dir, "outputs")
        if os.path.isdir(outputs_dir):
            for job in video.jobs:
                job_output_dir = os.path.join(outputs_dir, str(job.id))
                if os.path.isdir(job_output_dir):
                    shutil.rmtree(job_output_dir, ignore_errors=True)
                    logger.debug("Deleted output dir: %s", job_output_dir)
            # Remove outputs dir if empty
            try:
                os.rmdir(outputs_dir)
            except OSError:
                pass

        # Delete raw video file
        self.storage.delete_file(video.raw_video_path)

        self.db.delete(video)
        self.db.commit()
        logger.info("Video deleted: id=%s user=%s", video_id, user_id)

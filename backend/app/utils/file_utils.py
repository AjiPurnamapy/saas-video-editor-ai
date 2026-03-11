"""
File utility functions.

Common file system operations used across the application.
"""

import os
import shutil
import uuid
from typing import Optional


def ensure_directory(path: str) -> str:
    """Create a directory if it doesn't exist.

    Args:
        path: Directory path to create.

    Returns:
        The absolute path of the directory.
    """
    os.makedirs(path, exist_ok=True)
    return os.path.abspath(path)


def generate_unique_filename(
    original_filename: str,
    prefix: str = "",
) -> str:
    """Generate a unique filename preserving the original extension.

    Args:
        original_filename: The original file name.
        prefix: Optional prefix to prepend.

    Returns:
        A unique filename like 'prefix_uuid4.ext'.
    """
    ext = os.path.splitext(original_filename)[1].lower()
    unique_id = str(uuid.uuid4())
    if prefix:
        return f"{prefix}_{unique_id}{ext}"
    return f"{unique_id}{ext}"


def get_file_extension(filename: str) -> str:
    """Get the file extension in lowercase.

    Args:
        filename: The file name.

    Returns:
        The extension including the dot (e.g., '.mp4').
    """
    return os.path.splitext(filename)[1].lower()


def get_file_size_mb(path: str) -> Optional[float]:
    """Get file size in megabytes.

    Args:
        path: Path to the file.

    Returns:
        Size in MB, or None if the file doesn't exist.
    """
    if os.path.exists(path):
        return os.path.getsize(path) / (1024 * 1024)
    return None


def cleanup_temp_files(*paths: str) -> None:
    """Delete temporary files.

    Silently ignores files that don't exist.

    Args:
        *paths: File paths to delete.
    """
    for path in paths:
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except OSError:
            pass


def create_temp_directory(base_dir: str = "/tmp") -> str:
    """Create a unique temporary directory.

    Args:
        base_dir: Parent directory for the temp dir.

    Returns:
        Path to the newly created temp directory.
    """
    temp_dir = os.path.join(base_dir, f"aive_{uuid.uuid4().hex[:12]}")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

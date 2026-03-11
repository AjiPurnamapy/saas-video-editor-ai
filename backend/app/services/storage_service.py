"""
Storage service.

Abstraction layer for file storage operations. Currently implements
local filesystem storage with an interface ready for S3 migration.
"""

import os
from typing import Optional

from app.config import get_settings

settings = get_settings()


class StorageService:
    """File storage abstraction.

    Currently uses local filesystem storage. In production, this
    would be swapped for an S3-compatible implementation via
    boto3 (e.g., AWS S3, MinIO, DigitalOcean Spaces).
    """

    def save_file(self, content: bytes, path: str) -> str:
        """Save file content to storage.

        Creates parent directories if they don't exist.

        Args:
            content: Raw file bytes.
            path: Target storage path (relative or absolute).

        Returns:
            The path where the file was saved.
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
        return path

    def read_file(self, path: str) -> Optional[bytes]:
        """Read file content from storage.

        Args:
            path: The file path to read.

        Returns:
            File contents as bytes, or None if the file doesn't exist.
        """
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return f.read()

    def delete_file(self, path: str) -> bool:
        """Delete a file from storage.

        Args:
            path: The file path to delete.

        Returns:
            True if the file was deleted, False if it didn't exist.
        """
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def file_exists(self, path: str) -> bool:
        """Check if a file exists in storage.

        Args:
            path: The file path to check.

        Returns:
            True if the file exists.
        """
        return os.path.exists(path)

    def get_file_size(self, path: str) -> Optional[int]:
        """Get the size of a file in bytes.

        Args:
            path: The file path.

        Returns:
            File size in bytes, or None if the file doesn't exist.
        """
        if os.path.exists(path):
            return os.path.getsize(path)
        return None

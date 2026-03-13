"""
Storage service.

Abstraction layer for file storage operations. Uses the Strategy pattern
to support multiple storage backends (local filesystem, S3, etc.)
without changing consuming code.

Architecture:
    StorageBackend (ABC)        ← interface
      └── LocalStorageBackend   ← concrete (current)
      └── S3StorageBackend      ← concrete (future)

    StorageService(backend)     ← facade used by services/routes
"""

import logging
import os
from typing import Optional

from app.services.storage_base import StorageBackend

logger = logging.getLogger(__name__)


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend.

    Stores files on the local disk. This is the default backend
    for development and single-server deployments.
    """

    def save_file(self, content: bytes, path: str) -> str:
        """Save file content to local filesystem."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
        logger.debug("File saved: %s (%d bytes)", path, len(content))
        return path

    def read_file(self, path: str) -> Optional[bytes]:
        """Read file content from local filesystem."""
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return f.read()

    def delete_file(self, path: str) -> bool:
        """Delete a file from local filesystem."""
        if os.path.exists(path):
            os.remove(path)
            logger.debug("File deleted: %s", path)
            return True
        return False

    def file_exists(self, path: str) -> bool:
        """Check if a file exists on local filesystem."""
        return os.path.exists(path)

    def get_file_size(self, path: str) -> Optional[int]:
        """Get file size from local filesystem."""
        if os.path.exists(path):
            return os.path.getsize(path)
        return None


class StorageService:
    """File storage facade.

    Delegates all operations to the injected storage backend.
    Defaults to LocalStorageBackend if no backend is provided.

    Usage:
        # Default (local storage)
        storage = StorageService()

        # With explicit backend
        storage = StorageService(backend=LocalStorageBackend())

        # Future S3 support
        storage = StorageService(backend=S3StorageBackend(bucket="my-bucket"))
    """

    def __init__(self, backend: StorageBackend | None = None) -> None:
        """Initialize with a storage backend.

        Args:
            backend: Storage backend implementation. Defaults to local.
        """
        self._backend = backend or LocalStorageBackend()

    def save_file(self, content: bytes, path: str) -> str:
        """Save file content to storage."""
        return self._backend.save_file(content, path)

    def read_file(self, path: str) -> Optional[bytes]:
        """Read file content from storage."""
        return self._backend.read_file(path)

    def delete_file(self, path: str) -> bool:
        """Delete a file from storage."""
        return self._backend.delete_file(path)

    def file_exists(self, path: str) -> bool:
        """Check if a file exists in storage."""
        return self._backend.file_exists(path)

    def get_file_size(self, path: str) -> Optional[int]:
        """Get file size in bytes."""
        return self._backend.get_file_size(path)

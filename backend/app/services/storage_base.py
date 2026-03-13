"""
Storage backend abstract base class.

Defines the interface for all storage backends (local filesystem,
S3-compatible, etc.). New backends implement this ABC and are
injected into StorageService via its constructor.

To add S3 support later, create S3StorageBackend(StorageBackend)
without modifying any existing code.
"""

from abc import ABC, abstractmethod
from typing import Optional


class StorageBackend(ABC):
    """Abstract interface for file storage operations.

    All storage implementations (local, S3, GCS, etc.) must
    implement these methods. This enables swapping backends
    without changing service or route code.
    """

    @abstractmethod
    def save_file(self, content: bytes, path: str) -> str:
        """Save file content to storage.

        Args:
            content: Raw file bytes.
            path: Target storage path.

        Returns:
            The path/URL where the file was saved.
        """

    @abstractmethod
    def read_file(self, path: str) -> Optional[bytes]:
        """Read file content from storage.

        Args:
            path: The file path/key to read.

        Returns:
            File contents as bytes, or None if not found.
        """

    @abstractmethod
    def delete_file(self, path: str) -> bool:
        """Delete a file from storage.

        Args:
            path: The file path/key to delete.

        Returns:
            True if deleted, False if not found.
        """

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """Check if a file exists in storage.

        Args:
            path: The file path/key to check.

        Returns:
            True if the file exists.
        """

    @abstractmethod
    def get_file_size(self, path: str) -> Optional[int]:
        """Get the size of a file in bytes.

        Args:
            path: The file path/key.

        Returns:
            File size in bytes, or None if not found.
        """

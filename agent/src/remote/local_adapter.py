"""
Local filesystem adapter for unified file access.

Implements StorageAdapter interface for local directories, enabling
unified processing with remote collections (S3, GCS, SMB).

Design Pattern: Strategy pattern - same interface as remote adapters
"""

from pathlib import Path
from typing import List, Tuple

from src.remote.base import StorageAdapter, FileInfo


class LocalAdapter(StorageAdapter):
    """
    Local filesystem adapter.

    Implements StorageAdapter interface for local directories,
    enabling unified processing with remote collections.

    Example:
        >>> adapter = LocalAdapter({})
        >>> files = adapter.list_files("/path/to/photos")
        >>> files_with_metadata = adapter.list_files_with_metadata("/path/to/photos")
    """

    def __init__(self, credentials: dict):
        """
        Initialize LocalAdapter.

        Args:
            credentials: Empty dict (no credentials needed for local)
        """
        super().__init__(credentials)

    def list_files(self, location: str) -> List[str]:
        """
        List all files in local directory.

        Args:
            location: Local filesystem path

        Returns:
            List of file paths relative to location

        Raises:
            FileNotFoundError: If location doesn't exist
            PermissionError: If location isn't accessible
        """
        folder = Path(location).expanduser().resolve()

        if not folder.exists():
            raise FileNotFoundError(f"Path does not exist: {location}")

        if not folder.is_dir():
            raise ValueError(f"Path is not a directory: {location}")

        files = []
        for file_path in folder.rglob('*'):
            if file_path.is_file():
                try:
                    files.append(str(file_path.relative_to(folder)))
                except (PermissionError, OSError):
                    # Skip files we can't access
                    continue

        return files

    def list_files_with_metadata(self, location: str) -> List[FileInfo]:
        """
        List all files with metadata in local directory.

        Args:
            location: Local filesystem path

        Returns:
            List of FileInfo objects with path, size, and last_modified

        Raises:
            FileNotFoundError: If location doesn't exist
            PermissionError: If location isn't accessible
        """
        folder = Path(location).expanduser().resolve()

        if not folder.exists():
            raise FileNotFoundError(f"Path does not exist: {location}")

        if not folder.is_dir():
            raise ValueError(f"Path is not a directory: {location}")

        files = []
        for file_path in folder.rglob('*'):
            if file_path.is_file():
                try:
                    files.append(FileInfo.from_path_object(file_path, folder))
                except (PermissionError, OSError):
                    # Skip files we can't access
                    continue

        return files

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test that local filesystem access is available.

        For local adapter, this always returns True since we don't
        know the location until list_files() is called.

        Returns:
            Tuple of (True, "Local filesystem access available")
        """
        return True, "Local filesystem access available"

"""
Abstract base class for remote storage adapters.

Defines the interface for accessing remote storage systems (S3, GCS, SMB).
All concrete adapters must implement list_files() and test_connection() methods.

Design Pattern: Strategy pattern for pluggable storage backends
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional


@dataclass
class FileInfo:
    """
    Unified file information for both local and remote files.

    This is the canonical file representation for all storage backends,
    enabling shared analysis logic across local and remote collections.

    Attributes:
        path: File path relative to the storage location
        size: File size in bytes
        last_modified: Last modification timestamp (if available)
    """
    path: str
    size: int
    last_modified: Optional[str] = None

    @property
    def name(self) -> str:
        """Filename without directory (like Path.name)."""
        return self.path.rsplit('/', 1)[-1] if '/' in self.path else self.path

    @property
    def extension(self) -> str:
        """Extension with dot, lowercase (e.g., '.dng')."""
        name = self.name
        parts = name.rsplit('.', 1)
        return f".{parts[-1].lower()}" if len(parts) > 1 else ""

    @property
    def stem(self) -> str:
        """Filename without extension (like Path.stem)."""
        name = self.name
        return name.rsplit('.', 1)[0] if '.' in name else name

    @classmethod
    def from_path_object(cls, file_path: Path, base_path: Path) -> "FileInfo":
        """
        Create FileInfo from pathlib.Path (for local files).

        Args:
            file_path: Full path to the file
            base_path: Base path to calculate relative path from

        Returns:
            FileInfo instance with path relative to base_path
        """
        stat = file_path.stat()
        return cls(
            path=str(file_path.relative_to(base_path)),
            size=stat.st_size,
            last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat()
        )


class StorageAdapter(ABC):
    """
    Abstract base class for remote storage adapters.

    Provides a common interface for accessing different remote storage systems.
    Concrete implementations handle protocol-specific details (boto3, google-cloud-storage, smbprotocol).

    Methods:
        list_files(): List all files in the storage location (paths only)
        list_files_with_metadata(): List files with size and metadata
        test_connection(): Validate credentials and connectivity

    Usage:
        >>> adapter = S3Adapter(credentials)
        >>> files = adapter.list_files(location="bucket-name/prefix")
        >>> files_with_size = adapter.list_files_with_metadata(location="bucket-name/prefix")
        >>> success, message = adapter.test_connection()
    """

    def __init__(self, credentials: Dict[str, Any]):
        """
        Initialize storage adapter with credentials.

        Args:
            credentials: Decrypted credentials dictionary
                S3: {"aws_access_key_id": "...", "aws_secret_access_key": "...", "region": "us-west-2"}
                GCS: {"service_account_json": "..."}
                SMB: {"server": "...", "share": "...", "username": "...", "password": "..."}
        """
        self.credentials = credentials

    @abstractmethod
    def list_files(self, location: str) -> List[str]:
        """
        List all files at the specified location.

        Args:
            location: Storage location path
                S3: "bucket-name/optional/prefix"
                GCS: "bucket-name/optional/prefix"
                SMB: "/share-path/optional/prefix"

        Returns:
            List of file paths relative to location

        Raises:
            ConnectionError: If cannot connect to remote storage
            PermissionError: If credentials lack necessary permissions
            ValueError: If location is invalid

        Example:
            >>> files = adapter.list_files("my-bucket/photos")
            >>> print(files)
            ['photo1.jpg', 'photo2.dng', 'subfolder/photo3.jpg']
        """
        pass

    @abstractmethod
    def list_files_with_metadata(self, location: str) -> List[FileInfo]:
        """
        List all files with metadata (size, modification time) at the specified location.

        This method retrieves file metadata without downloading file contents,
        using HEAD requests or list operations that include metadata.

        Args:
            location: Storage location path
                S3: "bucket-name/optional/prefix"
                GCS: "bucket-name/optional/prefix"
                SMB: "/share-path/optional/prefix"

        Returns:
            List of FileInfo objects with path and size

        Raises:
            ConnectionError: If cannot connect to remote storage
            PermissionError: If credentials lack necessary permissions
            ValueError: If location is invalid

        Example:
            >>> files = adapter.list_files_with_metadata("my-bucket/photos")
            >>> for f in files:
            >>>     print(f"{f.path}: {f.size} bytes")
        """
        pass

    @abstractmethod
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to remote storage and validate credentials.

        Performs a lightweight operation to verify:
        - Credentials are valid
        - Network connectivity exists
        - Required permissions are present

        Returns:
            Tuple of (success: bool, message: str)
                success: True if connection successful, False otherwise
                message: Success message or error description

        Example:
            >>> success, message = adapter.test_connection()
            >>> if success:
            >>>     print(f"Connected: {message}")
            >>> else:
            >>>     print(f"Failed: {message}")
        """
        pass

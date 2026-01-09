"""
File listing adapters for local and remote collections.

Provides a unified interface for listing files with metadata (path, size)
across different storage backends (local filesystem, S3, GCS, SMB).

This module enables PhotoStats and Photo Pairing tools to work with
remote collections by abstracting away the storage-specific details.

Design Pattern: Strategy pattern with factory for adapter selection
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import List, Dict, Any, Optional, Set

from sqlalchemy.orm import Session

from backend.src.models import Collection, Connector
from backend.src.utils.logging_config import get_logger


logger = get_logger("services")


class VirtualPath:
    """
    Path-like object for remote files.

    Provides a minimal Path interface that can be used by PhotoStats and
    Photo Pairing tools without requiring actual filesystem access.

    This allows the tools to work with remote files (S3, GCS, SMB) using
    the same code paths as local files.

    Attributes:
        path: Full path string (e.g., "photos/2024/IMG_001.jpg")
        size: File size in bytes
        base_path: Base path for relative_to calculations

    Usage:
        >>> vp = VirtualPath("photos/2024/IMG_001.jpg", 1024, "photos")
        >>> vp.name  # "IMG_001.jpg"
        >>> vp.stem  # "IMG_001"
        >>> vp.suffix  # ".jpg"
        >>> vp.relative_to("photos")  # VirtualPath("2024/IMG_001.jpg")
    """

    def __init__(self, path: str, size: int = 0, base_path: str = ""):
        """
        Initialize VirtualPath.

        Args:
            path: Full path string
            size: File size in bytes
            base_path: Base path for this virtual filesystem
        """
        self._path = PurePosixPath(path)
        self._size = size
        self._base_path = base_path

    @property
    def name(self) -> str:
        """Return the final component of the path."""
        return self._path.name

    @property
    def stem(self) -> str:
        """Return the final component without suffix."""
        return self._path.stem

    @property
    def suffix(self) -> str:
        """Return the file extension."""
        return self._path.suffix

    @property
    def parent(self) -> "VirtualPath":
        """Return the parent path."""
        return VirtualPath(str(self._path.parent), 0, self._base_path)

    def relative_to(self, base) -> "VirtualPath":
        """Return path relative to base."""
        if isinstance(base, VirtualPath):
            base_str = str(base._path)
        elif isinstance(base, Path):
            base_str = str(base)
        else:
            base_str = str(base)

        try:
            rel = self._path.relative_to(base_str)
            return VirtualPath(str(rel), self._size, self._base_path)
        except ValueError:
            # If path doesn't start with base, return as-is
            return self

    def is_file(self) -> bool:
        """VirtualPath always represents a file."""
        return True

    def exists(self) -> bool:
        """VirtualPath always exists (it came from a file listing)."""
        return True

    def stat(self) -> "VirtualStat":
        """Return stat-like object with file size."""
        return VirtualStat(self._size)

    def __str__(self) -> str:
        return str(self._path)

    def __repr__(self) -> str:
        return f"VirtualPath({str(self._path)!r})"

    def __eq__(self, other) -> bool:
        if isinstance(other, VirtualPath):
            return str(self._path) == str(other._path)
        return str(self._path) == str(other)

    def __hash__(self) -> int:
        return hash(str(self._path))


class VirtualStat:
    """
    Minimal stat result for VirtualPath.

    Provides st_size attribute used by PhotoStats.
    """

    def __init__(self, size: int):
        self.st_size = size


@dataclass
class FileInfo:
    """
    Information about a file in a collection.

    Attributes:
        path: Relative path within the collection (e.g., "photos/2024/IMG_001.jpg")
        size: File size in bytes
        name: Filename without directory (e.g., "IMG_001.jpg")
        extension: File extension in lowercase (e.g., ".jpg")
    """
    path: str
    size: int
    name: str
    extension: str

    @classmethod
    def from_path(cls, path: str, size: int) -> "FileInfo":
        """Create FileInfo from a path string."""
        # Extract name and extension from path
        parts = path.rsplit("/", 1)
        name = parts[-1] if parts else path
        ext_parts = name.rsplit(".", 1)
        extension = f".{ext_parts[-1].lower()}" if len(ext_parts) > 1 else ""
        return cls(path=path, size=size, name=name, extension=extension)

    def to_virtual_path(self, base_path: str = "") -> VirtualPath:
        """Convert FileInfo to VirtualPath for use with CLI tools."""
        return VirtualPath(self.path, self.size, base_path)


class FileListingAdapter(ABC):
    """
    Abstract base class for file listing adapters.

    Provides a common interface for listing files with metadata from
    different storage backends. Concrete implementations handle
    storage-specific details.

    Methods:
        list_files(): List all files with metadata in the collection

    Usage:
        >>> adapter = LocalFileListingAdapter("/photos")
        >>> files = adapter.list_files()
        >>> for f in files:
        ...     print(f"{f.path}: {f.size} bytes")
    """

    @abstractmethod
    def list_files(self, extensions: Optional[Set[str]] = None) -> List[FileInfo]:
        """
        List all files in the collection.

        Args:
            extensions: Optional set of file extensions to filter by (e.g., {".jpg", ".dng"}).
                       Extensions should be lowercase with leading dot.
                       If None, returns all files.

        Returns:
            List of FileInfo objects containing path, size, name, and extension

        Raises:
            ConnectionError: If cannot connect to storage
            PermissionError: If credentials lack necessary permissions
            FileNotFoundError: If location does not exist
        """
        pass


class LocalFileListingAdapter(FileListingAdapter):
    """
    File listing adapter for local filesystem.

    Uses pathlib for efficient recursive directory traversal.

    Usage:
        >>> adapter = LocalFileListingAdapter("/photos/2024")
        >>> files = adapter.list_files(extensions={".jpg", ".dng"})
    """

    def __init__(self, location: str):
        """
        Initialize local adapter.

        Args:
            location: Absolute path to the local directory
        """
        self.location = Path(location)

    def list_files(self, extensions: Optional[Set[str]] = None) -> List[FileInfo]:
        """
        List all files in the local directory.

        Recursively scans the directory and returns file metadata.
        Skips files that cannot be accessed due to permissions.

        Args:
            extensions: Optional set of extensions to filter (lowercase with dot)

        Returns:
            List of FileInfo objects

        Raises:
            FileNotFoundError: If directory does not exist
        """
        if not self.location.exists():
            raise FileNotFoundError(f"Directory not found: {self.location}")

        if not self.location.is_dir():
            raise ValueError(f"Path is not a directory: {self.location}")

        # Normalize extensions to lowercase
        normalized_ext = None
        if extensions:
            normalized_ext = {ext.lower() for ext in extensions}

        files = []
        for file_path in self.location.rglob("*"):
            try:
                if not file_path.is_file():
                    continue

                # Get relative path from base location
                rel_path = str(file_path.relative_to(self.location))
                ext = file_path.suffix.lower()

                # Filter by extension if specified
                if normalized_ext and ext not in normalized_ext:
                    continue

                # Get file size
                try:
                    size = file_path.stat().st_size
                except (OSError, PermissionError):
                    size = 0

                files.append(FileInfo(
                    path=rel_path,
                    size=size,
                    name=file_path.name,
                    extension=ext
                ))

            except (PermissionError, OSError) as e:
                logger.warning(f"Cannot access file {file_path}: {e}")
                continue

        logger.info(f"Listed {len(files)} files from local directory {self.location}")
        return files


class S3FileListingAdapter(FileListingAdapter):
    """
    File listing adapter for Amazon S3.

    Wraps S3Adapter to provide file listing with size metadata.

    Usage:
        >>> adapter = S3FileListingAdapter(credentials, "my-bucket/photos")
        >>> files = adapter.list_files(extensions={".jpg", ".dng"})
    """

    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1.0
    BACKOFF_MULTIPLIER = 2.0

    def __init__(self, credentials: Dict[str, Any], location: str):
        """
        Initialize S3 adapter.

        Args:
            credentials: S3 credentials dict with aws_access_key_id, aws_secret_access_key, region
            location: S3 location in format "bucket-name" or "bucket-name/prefix"
        """
        import boto3
        from botocore.exceptions import NoCredentialsError

        if "aws_access_key_id" not in credentials:
            raise ValueError("Missing required credential: aws_access_key_id")
        if "aws_secret_access_key" not in credentials:
            raise ValueError("Missing required credential: aws_secret_access_key")

        region = credentials.get("region", "us-east-1")
        self.client = boto3.client(
            "s3",
            aws_access_key_id=credentials["aws_access_key_id"],
            aws_secret_access_key=credentials["aws_secret_access_key"],
            region_name=region
        )
        self.location = location

    def list_files(self, extensions: Optional[Set[str]] = None) -> List[FileInfo]:
        """
        List all files in S3 bucket/prefix with size metadata.

        Args:
            extensions: Optional set of extensions to filter (lowercase with dot)

        Returns:
            List of FileInfo objects with path relative to bucket root and size

        Raises:
            ConnectionError: If cannot connect after retries
            PermissionError: If credentials lack list permissions
        """
        import time
        from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError

        # Normalize extensions
        normalized_ext = None
        if extensions:
            normalized_ext = {ext.lower() for ext in extensions}

        # Parse bucket and prefix from location
        # Handle both "bucket/prefix" and "s3://bucket/prefix" formats
        location = self.location
        if location.startswith("s3://"):
            location = location[5:]  # Remove "s3://" prefix

        parts = location.split("/", 1)
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""

        files = []
        continuation_token = None

        for attempt in range(self.MAX_RETRIES):
            try:
                while True:
                    kwargs = {"Bucket": bucket, "Prefix": prefix}
                    if continuation_token:
                        kwargs["ContinuationToken"] = continuation_token

                    response = self.client.list_objects_v2(**kwargs)

                    if "Contents" in response:
                        for obj in response["Contents"]:
                            key = obj["Key"]
                            size = obj.get("Size", 0)

                            # Skip directory markers
                            if key.endswith("/"):
                                continue

                            # Create FileInfo and filter by extension
                            file_info = FileInfo.from_path(key, size)
                            if normalized_ext and file_info.extension not in normalized_ext:
                                continue

                            files.append(file_info)

                    if response.get("IsTruncated"):
                        continuation_token = response.get("NextContinuationToken")
                    else:
                        break

                logger.info(f"Listed {len(files)} files from S3 bucket {bucket}")
                return files

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")

                if error_code in ["AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"]:
                    raise PermissionError(
                        f"Access denied to S3 bucket '{bucket}'. "
                        f"Check credentials have s3:ListBucket permission."
                    )

                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.INITIAL_BACKOFF * (self.BACKOFF_MULTIPLIER ** attempt)
                    logger.warning(f"S3 list attempt {attempt + 1} failed, retrying in {backoff}s")
                    time.sleep(backoff)
                else:
                    raise ConnectionError(
                        f"Failed to list S3 bucket '{bucket}' after {self.MAX_RETRIES} attempts."
                    )

            except (NoCredentialsError, EndpointConnectionError) as e:
                raise ConnectionError(f"Cannot connect to S3: {str(e)}")

        return files


class GCSFileListingAdapter(FileListingAdapter):
    """
    File listing adapter for Google Cloud Storage.

    Wraps GCSAdapter to provide file listing with size metadata.

    Usage:
        >>> adapter = GCSFileListingAdapter(credentials, "my-bucket/photos")
        >>> files = adapter.list_files(extensions={".jpg", ".dng"})
    """

    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1.0
    BACKOFF_MULTIPLIER = 2.0

    def __init__(self, credentials: Dict[str, Any], location: str):
        """
        Initialize GCS adapter.

        Args:
            credentials: GCS credentials dict with service_account_json
            location: GCS location in format "bucket-name" or "bucket-name/prefix"
        """
        import json
        from google.cloud import storage

        if "service_account_json" not in credentials:
            raise ValueError("Missing required credential: service_account_json")

        try:
            service_account_info = json.loads(credentials["service_account_json"])
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid service_account_json format: {str(e)}")

        try:
            self.client = storage.Client.from_service_account_info(service_account_info)
        except Exception as e:
            raise ValueError(f"Failed to create GCS client: {str(e)}")

        self.location = location

    def list_files(self, extensions: Optional[Set[str]] = None) -> List[FileInfo]:
        """
        List all files in GCS bucket/prefix with size metadata.

        Args:
            extensions: Optional set of extensions to filter (lowercase with dot)

        Returns:
            List of FileInfo objects

        Raises:
            ConnectionError: If cannot connect after retries
            PermissionError: If credentials lack list permissions
        """
        import time
        from google.cloud.exceptions import GoogleCloudError, Forbidden, NotFound
        from google.auth.exceptions import GoogleAuthError

        # Normalize extensions
        normalized_ext = None
        if extensions:
            normalized_ext = {ext.lower() for ext in extensions}

        # Parse bucket and prefix from location
        # Handle both "bucket/prefix" and "gs://bucket/prefix" formats
        location = self.location
        if location.startswith("gs://"):
            location = location[5:]  # Remove "gs://" prefix

        parts = location.split("/", 1)
        bucket_name = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""

        files = []

        for attempt in range(self.MAX_RETRIES):
            try:
                bucket = self.client.bucket(bucket_name)
                blobs = bucket.list_blobs(prefix=prefix)

                for blob in blobs:
                    # Skip directory markers
                    if blob.name.endswith("/"):
                        continue

                    file_info = FileInfo.from_path(blob.name, blob.size or 0)
                    if normalized_ext and file_info.extension not in normalized_ext:
                        continue

                    files.append(file_info)

                logger.info(f"Listed {len(files)} files from GCS bucket {bucket_name}")
                return files

            except (Forbidden, GoogleAuthError) as e:
                raise PermissionError(
                    f"Access denied to GCS bucket '{bucket_name}'. "
                    f"Check service account has storage.objects.list permission."
                )

            except NotFound:
                raise FileNotFoundError(f"GCS bucket '{bucket_name}' not found")

            except GoogleCloudError as e:
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.INITIAL_BACKOFF * (self.BACKOFF_MULTIPLIER ** attempt)
                    logger.warning(f"GCS list attempt {attempt + 1} failed, retrying in {backoff}s")
                    time.sleep(backoff)
                else:
                    raise ConnectionError(
                        f"Failed to list GCS bucket '{bucket_name}' after {self.MAX_RETRIES} attempts."
                    )

        return files


class SMBFileListingAdapter(FileListingAdapter):
    """
    File listing adapter for SMB/CIFS network shares.

    Wraps SMBAdapter to provide file listing with size metadata.

    Usage:
        >>> adapter = SMBFileListingAdapter(credentials, "/subfolder")
        >>> files = adapter.list_files(extensions={".jpg", ".dng"})
    """

    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1.0
    BACKOFF_MULTIPLIER = 2.0

    def __init__(self, credentials: Dict[str, Any], location: str):
        """
        Initialize SMB adapter.

        Args:
            credentials: SMB credentials dict with server, share, username, password, optional port
            location: Path within the share (e.g., "/photos/2024")
        """
        from smbclient import register_session

        required = ["server", "share", "username", "password"]
        for key in required:
            if key not in credentials:
                raise ValueError(f"Missing required credential: {key}")

        self.server = credentials["server"]
        self.share = credentials["share"]
        self.username = credentials["username"]
        self.password = credentials["password"]
        self.port = credentials.get("port", 445)
        self.location = location.lstrip("/") if location else ""

        # Register SMB session
        try:
            register_session(
                server=self.server,
                username=self.username,
                password=self.password,
                port=self.port
            )
        except Exception as e:
            raise ValueError(f"Failed to register SMB session: {str(e)}")

    def _build_smb_path(self, subpath: str = "") -> str:
        """Build UNC path for SMB access."""
        base = f"//{self.server}/{self.share}"
        if self.location:
            base = f"{base}/{self.location}"
        if subpath:
            base = f"{base}/{subpath}"
        return base

    def _list_recursive(self, path: str, normalized_ext: Optional[Set[str]]) -> List[FileInfo]:
        """Recursively list files in SMB path."""
        import time
        from smbclient import listdir, stat
        from smbprotocol.exceptions import SMBConnectionClosed, SMBAuthenticationError, SMBOSError

        files = []

        for attempt in range(self.MAX_RETRIES):
            try:
                entries = listdir(path)
                for entry in entries:
                    full_path = f"{path}/{entry}"

                    try:
                        file_stat = stat(full_path)
                    except (SMBOSError, PermissionError):
                        continue

                    # Check if directory
                    import stat as stat_module
                    if stat_module.S_ISDIR(file_stat.st_mode):
                        # Recurse into subdirectory
                        files.extend(self._list_recursive(full_path, normalized_ext))
                    else:
                        # It's a file
                        # Calculate relative path from base location
                        base_path = self._build_smb_path()
                        rel_path = full_path[len(base_path):].lstrip("/")

                        file_info = FileInfo.from_path(rel_path, file_stat.st_size)
                        if normalized_ext and file_info.extension not in normalized_ext:
                            continue

                        files.append(file_info)

                return files

            except SMBConnectionClosed:
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.INITIAL_BACKOFF * (self.BACKOFF_MULTIPLIER ** attempt)
                    logger.warning(f"SMB connection closed, retrying in {backoff}s")
                    time.sleep(backoff)
                    # Re-register session
                    from smbclient import register_session
                    register_session(
                        server=self.server,
                        username=self.username,
                        password=self.password,
                        port=self.port
                    )
                else:
                    raise ConnectionError(
                        f"SMB connection failed after {self.MAX_RETRIES} attempts"
                    )

            except SMBAuthenticationError:
                raise PermissionError(
                    f"SMB authentication failed for {self.server}/{self.share}"
                )

            except SMBOSError as e:
                raise ConnectionError(f"SMB error: {str(e)}")

        return files

    def list_files(self, extensions: Optional[Set[str]] = None) -> List[FileInfo]:
        """
        List all files in SMB share with size metadata.

        Args:
            extensions: Optional set of extensions to filter (lowercase with dot)

        Returns:
            List of FileInfo objects

        Raises:
            ConnectionError: If cannot connect after retries
            PermissionError: If credentials are invalid
        """
        normalized_ext = None
        if extensions:
            normalized_ext = {ext.lower() for ext in extensions}

        base_path = self._build_smb_path()
        files = self._list_recursive(base_path, normalized_ext)

        logger.info(f"Listed {len(files)} files from SMB share {self.server}/{self.share}")
        return files


class FileListingFactory:
    """
    Factory for creating appropriate FileListingAdapter based on collection type.

    Usage:
        >>> adapter = FileListingFactory.create_adapter(collection, db_session)
        >>> files = adapter.list_files(extensions={".jpg", ".dng"})
    """

    @staticmethod
    def create_adapter(
        collection: Collection,
        db: Session,
        encryptor: Optional[Any] = None
    ) -> FileListingAdapter:
        """
        Create appropriate adapter for the collection type.

        Args:
            collection: Collection model instance
            db: Database session for loading connector credentials
            encryptor: Optional encryptor for decrypting credentials

        Returns:
            FileListingAdapter implementation for the collection type

        Raises:
            ValueError: If collection type is not supported or connector not found
        """
        # Handle both enum (real model) and string (tests/mocks) types
        raw_type = collection.type
        collection_type = (raw_type.value if hasattr(raw_type, 'value') else raw_type).lower()

        if collection_type == "local":
            return LocalFileListingAdapter(collection.location)

        # Remote collections require a connector with credentials
        if not collection.connector_id:
            raise ValueError(
                f"Remote collection '{collection.name}' requires a connector"
            )

        connector = db.query(Connector).filter(
            Connector.id == collection.connector_id
        ).first()

        if not connector:
            raise ValueError(
                f"Connector {collection.connector_id} not found for collection '{collection.name}'"
            )

        # Decrypt credentials
        if encryptor and connector.credentials:
            credentials = encryptor.decrypt_dict(connector.credentials)
        else:
            # For testing without encryption (credentials already a dict)
            credentials = connector.credentials if isinstance(connector.credentials, dict) else {}

        if collection_type == "s3":
            return S3FileListingAdapter(credentials, collection.location)

        elif collection_type == "gcs":
            return GCSFileListingAdapter(credentials, collection.location)

        elif collection_type == "smb":
            return SMBFileListingAdapter(credentials, collection.location)

        else:
            raise ValueError(f"Unsupported collection type: {collection_type}")

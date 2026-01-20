"""
Google Cloud Storage adapter implementation.

Provides access to Google Cloud Storage using google-cloud-storage library.
Implements exponential backoff retry for transient failures (FR-012: 3 retries).
"""

import json
import logging
import time
from typing import List, Dict, Any, Tuple

from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError, Forbidden, NotFound
from google.auth.exceptions import GoogleAuthError

from src.remote.base import StorageAdapter, FileInfo


logger = logging.getLogger("shuttersense.agent.remote.gcs")


class GCSAdapter(StorageAdapter):
    """
    Google Cloud Storage adapter.

    Implements remote file access for Google Cloud Storage using service account authentication.
    Uses google-cloud-storage library with exponential backoff retry for reliability.

    Credentials Format:
        {
            "service_account_json": "{...}"  # JSON string of service account key
        }

    Service Account JSON Structure:
        {
            "type": "service_account",
            "project_id": "my-project",
            "private_key_id": "...",
            "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
            "client_email": "my-service-account@my-project.iam.gserviceaccount.com",
            "client_id": "...",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            ...
        }

    Features:
        - Exponential backoff retry (3 attempts per FR-012)
        - Paginated listing for large buckets
        - Service account authentication
        - Comprehensive error handling with actionable messages

    Usage:
        >>> credentials = {"service_account_json": "{...}"}
        >>> adapter = GCSAdapter(credentials)
        >>> files = adapter.list_files("my-bucket/photos")
        >>> success, msg = adapter.test_connection()
    """

    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1.0  # seconds
    BACKOFF_MULTIPLIER = 2.0

    def __init__(self, credentials: Dict[str, Any]):
        """
        Initialize GCS adapter with service account credentials.

        Args:
            credentials: Dictionary with service_account_json key

        Raises:
            ValueError: If required credential keys are missing or invalid
        """
        super().__init__(credentials)

        # Validate required credentials
        if "service_account_json" not in credentials:
            raise ValueError("Missing required credential: service_account_json")

        # Parse service account JSON
        try:
            service_account_info = json.loads(credentials["service_account_json"])
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid service_account_json format: {str(e)}")

        # Create GCS client from service account info
        try:
            self.client = storage.Client.from_service_account_info(service_account_info)
        except Exception as e:
            raise ValueError(f"Failed to create GCS client from service account: {str(e)}")

    def list_files(self, location: str) -> List[str]:
        """
        List all files in GCS bucket/prefix.

        Implements paginated listing with exponential backoff retry.
        Only returns blob objects (excludes directory markers).

        Args:
            location: GCS location in format "bucket-name" or "bucket-name/prefix"

        Returns:
            List of blob names relative to bucket root

        Raises:
            ValueError: If location format is invalid
            ConnectionError: If cannot connect after retries
            PermissionError: If credentials lack list permissions

        Example:
            >>> files = adapter.list_files("my-bucket/photos/2024")
            >>> print(files)
            ['photos/2024/IMG_001.jpg', 'photos/2024/IMG_002.dng']
        """
        # Parse bucket and prefix from location
        parts = location.split("/", 1)
        bucket_name = parts[0]
        prefix = parts[1] if len(parts) > 1 else None

        files = []

        for attempt in range(self.MAX_RETRIES):
            try:
                bucket = self.client.bucket(bucket_name)

                # List blobs with prefix
                blobs = bucket.list_blobs(prefix=prefix)

                for blob in blobs:
                    # Skip directory markers (end with /)
                    if not blob.name.endswith("/"):
                        files.append(blob.name)

                logger.info(
                    f"Listed {len(files)} files from GCS bucket={bucket_name} prefix={prefix}"
                )
                return files

            except Forbidden as e:
                logger.error(f"GCS permission error bucket={bucket_name} error={e}")
                raise PermissionError(
                    f"Access denied to GCS bucket '{bucket_name}'. "
                    f"Check service account has storage.objects.list permission. Error: {str(e)}"
                )

            except NotFound as e:
                logger.error(f"GCS bucket not found: {bucket_name}")
                raise ValueError(f"GCS bucket '{bucket_name}' not found: {str(e)}")

            except GoogleCloudError as e:
                # Retry transient errors
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.INITIAL_BACKOFF * (self.BACKOFF_MULTIPLIER ** attempt)
                    logger.warning(
                        f"GCS list_files attempt {attempt + 1} failed, retrying in {backoff}s error={e}"
                    )
                    time.sleep(backoff)
                else:
                    logger.error(f"GCS list_files failed after {self.MAX_RETRIES} attempts")
                    raise ConnectionError(
                        f"Failed to list GCS bucket '{bucket_name}' after {self.MAX_RETRIES} attempts. "
                        f"Last error: {str(e)}"
                    )

            except Exception as e:
                logger.error(f"GCS unexpected error: {e} bucket={bucket_name}")
                raise ConnectionError(f"Unexpected error accessing GCS: {str(e)}")

        return files

    def list_files_with_metadata(self, location: str) -> List[FileInfo]:
        """
        List all files with metadata (size, modification time) in GCS bucket/prefix.

        Uses blob properties which are included in the list operation.
        No additional API calls needed beyond the listing operation.

        Args:
            location: GCS location in format "bucket-name" or "bucket-name/prefix"

        Returns:
            List of FileInfo objects with path, size, and last_modified

        Raises:
            ValueError: If location format is invalid
            ConnectionError: If cannot connect after retries
            PermissionError: If credentials lack list permissions
        """
        # Parse bucket and prefix from location
        parts = location.split("/", 1)
        bucket_name = parts[0]
        prefix = parts[1] if len(parts) > 1 else None

        files: List[FileInfo] = []

        for attempt in range(self.MAX_RETRIES):
            try:
                bucket = self.client.bucket(bucket_name)

                # List blobs with prefix - includes size and updated properties
                blobs = bucket.list_blobs(prefix=prefix)

                for blob in blobs:
                    # Skip directory markers (end with /)
                    if not blob.name.endswith("/"):
                        files.append(FileInfo(
                            path=blob.name,
                            size=blob.size or 0,
                            last_modified=blob.updated.isoformat() if blob.updated else None
                        ))

                total_size = sum(f.size for f in files)
                logger.info(
                    f"Listed {len(files)} files ({total_size} bytes) from GCS bucket={bucket_name} prefix={prefix}"
                )
                return files

            except Forbidden as e:
                logger.error(f"GCS permission error bucket={bucket_name} error={e}")
                raise PermissionError(
                    f"Access denied to GCS bucket '{bucket_name}'. "
                    f"Check service account has storage.objects.list permission. Error: {str(e)}"
                )

            except NotFound as e:
                logger.error(f"GCS bucket not found: {bucket_name}")
                raise ValueError(f"GCS bucket '{bucket_name}' not found: {str(e)}")

            except GoogleCloudError as e:
                # Retry transient errors
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.INITIAL_BACKOFF * (self.BACKOFF_MULTIPLIER ** attempt)
                    logger.warning(
                        f"GCS list_files_with_metadata attempt {attempt + 1} failed, retrying in {backoff}s error={e}"
                    )
                    time.sleep(backoff)
                else:
                    logger.error(f"GCS list_files_with_metadata failed after {self.MAX_RETRIES} attempts")
                    raise ConnectionError(
                        f"Failed to list GCS bucket '{bucket_name}' after {self.MAX_RETRIES} attempts. "
                        f"Last error: {str(e)}"
                    )

            except Exception as e:
                logger.error(f"GCS unexpected error: {e} bucket={bucket_name}")
                raise ConnectionError(f"Unexpected error accessing GCS: {str(e)}")

        return files

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test GCS connection by listing buckets.

        Validates service account credentials and network connectivity.

        Returns:
            Tuple of (success: bool, message: str)

        Example:
            >>> success, message = adapter.test_connection()
            >>> print(f"GCS connection: {message}")
        """
        try:
            # List buckets to test credentials (lightweight operation)
            buckets = list(self.client.list_buckets())
            bucket_count = len(buckets)

            logger.info(f"GCS connection test successful bucket_count={bucket_count}")
            return True, f"Connected to Google Cloud Storage. Found {bucket_count} accessible buckets."

        except GoogleAuthError as e:
            logger.error(f"GCS authentication error: {e}")
            return False, f"Invalid service account credentials: {str(e)}"

        except Forbidden as e:
            logger.error(f"GCS permission error: {e}")
            return False, f"Service account lacks required permissions. Check IAM roles: {str(e)}"

        except GoogleCloudError as e:
            logger.error(f"GCS connection test failed: {e}")
            return False, f"GCS connection failed: {str(e)}"

        except Exception as e:
            logger.error(f"GCS connection test unexpected error: {e}")
            return False, f"Unexpected error testing GCS connection: {str(e)}"

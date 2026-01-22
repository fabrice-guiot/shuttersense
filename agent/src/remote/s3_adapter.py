"""
Amazon S3 storage adapter implementation.

Provides access to AWS S3 (and S3-compatible storage) using boto3.
Implements exponential backoff retry for transient failures (FR-012: 3 retries).
"""

import logging
import time
from typing import List, Dict, Any, Tuple

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError

from src.remote.base import StorageAdapter, FileInfo


logger = logging.getLogger("shuttersense.agent.remote.s3")


class S3Adapter(StorageAdapter):
    """
    AWS S3 storage adapter.

    Implements remote file access for Amazon S3 and S3-compatible storage systems.
    Uses boto3 client with exponential backoff retry for reliability.

    Credentials Format:
        {
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "region": "us-west-2"  # Optional, defaults to us-east-1
        }

    Features:
        - Exponential backoff retry (3 attempts per FR-012)
        - Paginated listing for large buckets
        - Connection pooling via boto3 session
        - Comprehensive error handling with actionable messages

    Usage:
        >>> credentials = {"aws_access_key_id": "...", "aws_secret_access_key": "..."}
        >>> adapter = S3Adapter(credentials)
        >>> files = adapter.list_files("my-bucket/photos")
        >>> success, msg = adapter.test_connection()
    """

    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1.0  # seconds
    BACKOFF_MULTIPLIER = 2.0

    def __init__(self, credentials: Dict[str, Any]):
        """
        Initialize S3 adapter with credentials.

        Args:
            credentials: Dictionary with aws_access_key_id, aws_secret_access_key, and optional region

        Raises:
            ValueError: If required credential keys are missing
        """
        super().__init__(credentials)

        # Validate required credentials
        if "aws_access_key_id" not in credentials:
            raise ValueError("Missing required credential: aws_access_key_id")
        if "aws_secret_access_key" not in credentials:
            raise ValueError("Missing required credential: aws_secret_access_key")

        # Create boto3 client
        region = credentials.get("region", "us-east-1")
        self.client = boto3.client(
            "s3",
            aws_access_key_id=credentials["aws_access_key_id"],
            aws_secret_access_key=credentials["aws_secret_access_key"],
            region_name=region
        )

    def list_files(self, location: str) -> List[str]:
        """
        List all files in S3 bucket/prefix.

        Implements paginated listing with exponential backoff retry.
        Only returns file objects (excludes directories).

        Args:
            location: S3 location in format "bucket-name" or "bucket-name/prefix"

        Returns:
            List of file keys relative to bucket root

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
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""

        files = []
        continuation_token = None

        for attempt in range(self.MAX_RETRIES):
            try:
                # Paginated listing
                while True:
                    kwargs = {
                        "Bucket": bucket,
                        "Prefix": prefix
                    }
                    if continuation_token:
                        kwargs["ContinuationToken"] = continuation_token

                    response = self.client.list_objects_v2(**kwargs)

                    # Extract file keys (exclude directories)
                    if "Contents" in response:
                        for obj in response["Contents"]:
                            key = obj["Key"]
                            # Skip if it's a directory marker (ends with /)
                            if not key.endswith("/"):
                                files.append(key)

                    # Check if more pages exist
                    if response.get("IsTruncated"):
                        continuation_token = response.get("NextContinuationToken")
                    else:
                        break

                logger.info(
                    f"Listed {len(files)} files from S3 bucket={bucket} prefix={prefix}"
                )
                return files

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")

                # Don't retry permission errors
                if error_code in ["AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"]:
                    logger.error(f"S3 permission error: {error_code} bucket={bucket}")
                    raise PermissionError(
                        f"Access denied to S3 bucket '{bucket}'. "
                        f"Check credentials have s3:ListBucket permission. Error: {error_code}"
                    )

                # Retry transient errors
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.INITIAL_BACKOFF * (self.BACKOFF_MULTIPLIER ** attempt)
                    logger.warning(
                        f"S3 list_files attempt {attempt + 1} failed, retrying in {backoff}s error={e}"
                    )
                    time.sleep(backoff)
                else:
                    logger.error(f"S3 list_files failed after {self.MAX_RETRIES} attempts")
                    raise ConnectionError(
                        f"Failed to list S3 bucket '{bucket}' after {self.MAX_RETRIES} attempts. "
                        f"Last error: {str(e)}"
                    )

            except (NoCredentialsError, EndpointConnectionError) as e:
                logger.error(f"S3 connection error: {e} bucket={bucket}")
                raise ConnectionError(f"Cannot connect to S3: {str(e)}")

        return files

    def list_files_with_metadata(self, location: str) -> List[FileInfo]:
        """
        List all files with metadata (size, modification time) in S3 bucket/prefix.

        Uses list_objects_v2 which returns Size and LastModified for each object.
        No additional API calls needed beyond the listing operation.

        Args:
            location: S3 location in format "bucket-name" or "bucket-name/prefix"

        Returns:
            List of FileInfo objects with path, size, and last_modified

        Raises:
            ValueError: If location format is invalid
            ConnectionError: If cannot connect after retries
            PermissionError: If credentials lack list permissions
        """
        # Parse bucket and prefix from location
        parts = location.split("/", 1)
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""

        files: List[FileInfo] = []
        continuation_token = None

        for attempt in range(self.MAX_RETRIES):
            try:
                # Paginated listing
                while True:
                    kwargs = {
                        "Bucket": bucket,
                        "Prefix": prefix
                    }
                    if continuation_token:
                        kwargs["ContinuationToken"] = continuation_token

                    response = self.client.list_objects_v2(**kwargs)

                    # Extract file info with metadata
                    if "Contents" in response:
                        for obj in response["Contents"]:
                            key = obj["Key"]
                            # Skip if it's a directory marker (ends with /)
                            if not key.endswith("/"):
                                last_modified = obj.get("LastModified")
                                files.append(FileInfo(
                                    path=key,
                                    size=obj["Size"],
                                    last_modified=last_modified.isoformat() if last_modified else None
                                ))

                    # Check if more pages exist
                    if response.get("IsTruncated"):
                        continuation_token = response.get("NextContinuationToken")
                    else:
                        break

                total_size = sum(f.size for f in files)
                logger.info(
                    f"Listed {len(files)} files ({total_size} bytes) from S3 bucket={bucket} prefix={prefix}"
                )
                return files

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")

                # Don't retry permission errors
                if error_code in ["AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"]:
                    logger.error(f"S3 permission error: {error_code} bucket={bucket}")
                    raise PermissionError(
                        f"Access denied to S3 bucket '{bucket}'. "
                        f"Check credentials have s3:ListBucket permission. Error: {error_code}"
                    )

                # Retry transient errors
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self.INITIAL_BACKOFF * (self.BACKOFF_MULTIPLIER ** attempt)
                    logger.warning(
                        f"S3 list_files_with_metadata attempt {attempt + 1} failed, retrying in {backoff}s error={e}"
                    )
                    time.sleep(backoff)
                else:
                    logger.error(f"S3 list_files_with_metadata failed after {self.MAX_RETRIES} attempts")
                    raise ConnectionError(
                        f"Failed to list S3 bucket '{bucket}' after {self.MAX_RETRIES} attempts. "
                        f"Last error: {str(e)}"
                    )

            except (NoCredentialsError, EndpointConnectionError) as e:
                logger.error(f"S3 connection error: {e} bucket={bucket}")
                raise ConnectionError(f"Cannot connect to S3: {str(e)}")

        return files

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test S3 connection by listing buckets.

        Validates credentials and network connectivity with a lightweight operation.

        Returns:
            Tuple of (success: bool, message: str)

        Example:
            >>> success, message = adapter.test_connection()
            >>> print(f"S3 connection: {message}")
        """
        try:
            # List buckets to test credentials (lightweight operation)
            response = self.client.list_buckets()
            bucket_count = len(response.get("Buckets", []))

            logger.info(f"S3 connection test successful bucket_count={bucket_count}")
            return True, f"Connected to AWS S3. Found {bucket_count} accessible buckets."

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))

            logger.error(f"S3 connection test failed: {error_code} error={error_msg}")

            if error_code == "InvalidAccessKeyId":
                return False, "Invalid AWS Access Key ID. Check credentials."
            elif error_code == "SignatureDoesNotMatch":
                return False, "Invalid AWS Secret Access Key. Check credentials."
            elif error_code == "AccessDenied":
                return False, f"Access denied. Check IAM permissions: {error_msg}"
            else:
                return False, f"S3 connection failed: {error_msg}"

        except NoCredentialsError:
            logger.error("S3 connection test failed: No credentials provided")
            return False, "No AWS credentials provided."

        except EndpointConnectionError as e:
            logger.error(f"S3 connection test failed: Cannot reach endpoint - {e}")
            return False, f"Cannot connect to S3 endpoint. Check network connectivity: {str(e)}"

        except Exception as e:
            logger.error(f"S3 connection test failed with unexpected error: {e}")
            return False, f"Unexpected error testing S3 connection: {str(e)}"

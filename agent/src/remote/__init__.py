"""
Remote storage adapters for accessing S3, GCS, and SMB storage systems.

This package provides a unified interface for accessing different remote storage backends
through the StorageAdapter abstract base class. Used by the agent to list files
in remote collections without downloading them.

Adapters:
- S3Adapter: Amazon S3 and S3-compatible storage (boto3)
- GCSAdapter: Google Cloud Storage (google-cloud-storage)
- SMBAdapter: SMB/CIFS network shares (smbprotocol)

Usage:
    >>> from src.remote import S3Adapter
    >>> credentials = {"aws_access_key_id": "...", "aws_secret_access_key": "..."}
    >>> adapter = S3Adapter(credentials)
    >>> files = adapter.list_files("bucket-name/prefix")
    >>> success, message = adapter.test_connection()
"""

from src.remote.base import StorageAdapter, FileInfo
from src.remote.s3_adapter import S3Adapter
from src.remote.gcs_adapter import GCSAdapter
from src.remote.smb_adapter import SMBAdapter
from src.remote.local_adapter import LocalAdapter

__all__ = [
    "StorageAdapter",
    "FileInfo",
    "S3Adapter",
    "GCSAdapter",
    "SMBAdapter",
    "LocalAdapter",
]

"""
Remote storage adapters for accessing S3, GCS, and SMB storage systems.

This package provides a unified interface for accessing different remote storage backends
through the StorageAdapter abstract base class. Used by the agent to list files
in remote collections without downloading them.

Adapters:
- S3Adapter: Amazon S3 and S3-compatible storage (boto3)
- GCSAdapter: Google Cloud Storage (google-cloud-storage)
- SMBAdapter: SMB/CIFS network shares (smbprotocol)
- LocalAdapter: Local filesystem (no dependencies)

Usage:
    >>> from src.remote import S3Adapter
    >>> credentials = {"aws_access_key_id": "...", "aws_secret_access_key": "..."}
    >>> adapter = S3Adapter(credentials)
    >>> files = adapter.list_files("bucket-name/prefix")
    >>> success, message = adapter.test_connection()

Note:
    Cloud adapters (S3, GCS, SMB) are lazily imported to avoid requiring their
    dependencies when only local filesystem access is needed.
"""

from src.remote.base import StorageAdapter, FileInfo
from src.remote.local_adapter import LocalAdapter

# Lazy imports for cloud adapters to avoid requiring boto3/google-cloud-storage/smbprotocol
# when they're not needed (e.g., in tests that only use local filesystem)
_lazy_imports = {
    "S3Adapter": "src.remote.s3_adapter",
    "GCSAdapter": "src.remote.gcs_adapter",
    "SMBAdapter": "src.remote.smb_adapter",
}


def __getattr__(name: str):
    """Lazily import cloud adapters when accessed."""
    if name in _lazy_imports:
        import importlib
        module = importlib.import_module(_lazy_imports[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "StorageAdapter",
    "FileInfo",
    "S3Adapter",
    "GCSAdapter",
    "SMBAdapter",
    "LocalAdapter",
]
